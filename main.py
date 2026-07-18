from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
import pandas as pd
import numpy as np
import time

app = Flask(__name__)
CORS(app)

# All Pocket Option Forex and Crypto pairs mapping
MARKETS = {
    "EURUSD": {"tv_symbol": "FX:EURUSD", "type": "forex"},
    "GBPUSD": {"tv_symbol": "FX:GBPUSD", "type": "forex"},
    "USDJPY": {"tv_symbol": "FX:USDJPY", "type": "forex"},
    "AUDUSD": {"tv_symbol": "FX:AUDUSD", "type": "forex"},
    "USDCAD": {"tv_symbol": "FX:USDCAD", "type": "forex"},
    "USDCHF": {"tv_symbol": "FX:USDCHF", "type": "forex"},
    "NZDUSD": {"tv_symbol": "FX:NZDUSD", "type": "forex"},
    "BTCUSDT": {"tv_symbol": "BINANCE:BTCUSDT", "type": "crypto"},
    "ETHUSDT": {"tv_symbol": "BINANCE:ETHUSDT", "type": "crypto"}
}

def fetch_market_data(symbol, mtype):
    if mtype == "crypto":
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50"
        try:
            response = requests.get(url).json()
            closes = [float(candle[4]) for candle in response]
            return pd.Series(closes)
        except:
            return pd.Series([])
    else:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}=X?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(url, headers=headers).json()
            closes = res['chart']['result'][0]['indicators']['quote'][0]['close']
            closes = [c for c in closes if c is not None][-50:]
            return pd.Series(closes)
        except:
            return pd.Series([])

def calculate_rsi(prices, period=14):
    if len(prices) < period:
        return 50
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QUNTEAM AI - Live Pro Dashboard</title>
    <style>
        body {
            background-color: #0d1117;
            color: #c9d1d9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 10px;
            box-sizing: border-box;
        }
        .container {
            display: flex;
            flex-direction: row;
            gap: 15px;
            max-width: 1100px;
            width: 100%;
        }
        .card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            flex: 1;
            max-width: 340px;
        }
        .chart-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 10px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            flex: 2;
            height: 500px;
        }
        h1 { font-size: 22px; margin-bottom: 5px; color: #58a6ff; margin-top: 0; }
        .select-box {
            background-color: #21262d;
            color: #c9d1d9;
            border: 1px solid #30363d;
            padding: 10px;
            border-radius: 6px;
            width: 100%;
            font-size: 15px;
            margin-bottom: 15px;
            outline: none;
            cursor: pointer;
        }
        .signal-box {
            font-size: 34px;
            font-weight: bold;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 15px;
            letter-spacing: 2px;
        }
        .CALL { background-color: rgba(46, 160, 67, 0.15); color: #3fb950; border: 1px solid #2ea043; }
        .PUT { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
        .WAITING { background-color: rgba(139, 148, 158, 0.15); color: #8b949e; border: 1px solid #30363d; }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #21262d;
        }
        .stat-row:last-child { border-bottom: none; }
        .label { color: #8b949e; }
        .value { font-weight: 600; color: #f0f6fc; }
        .timer-box {
            font-size: 16px;
            font-weight: bold;
            color: #ffc107;
            background: rgba(255, 193, 7, 0.1);
            padding: 8px;
            border-radius: 6px;
            margin-bottom: 15px;
            border: 1px solid rgba(255, 193, 7, 0.3);
        }
        
        @media (max-width: 768px) {
            .container { flex-direction: column; align-items: center; }
            .card, .chart-card { width: 100%; max-width: 100%; }
            .chart-card { height: 350px; }
        }
    </style>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script>
        let tvWidget;
        const marketTvMap = {
            "EURUSD": "FX:EURUSD", "GBPUSD": "FX:GBPUSD", "USDJPY": "FX:USDJPY",
            "AUDUSD": "FX:AUDUSD", "USDCAD": "FX:USDCAD", "USDCHF": "FX:USDCHF",
            "NZDUSD": "FX:NZDUSD", "BTCUSDT": "BINANCE:BTCUSDT", "ETHUSDT": "BINANCE:ETHUSDT"
        };

        function startTimer() {
            setInterval(() => {
                const now = new Date();
                const secondsLeft = 60 - now.getSeconds();
                document.getElementById('timer').innerText = "Candle Close In: " + secondsLeft + "s";
                
                if (secondsLeft === 60 || secondsLeft === 30 || secondsLeft === 1) {
                    fetchSignal();
                }
            }, 1000);
        }

        function loadChart(symbol) {
            tvWidget = new TradingView.widget({
                "width": "100%", "height": "100%", "symbol": symbol,
                "interval": "1", "timezone": "Etc/UTC", "theme": "dark",
                "style": "1", "locale": "en", "enable_publishing": false,
                "hide_side_toolbar": false, "allow_symbol_change": false,
                "container_id": "tv-chart-container"
            });
        }
        
        async function fetchSignal() {
            const market = document.getElementById('marketSelect').value;
            try {
                const res = await fetch('/api/signals/' + market);
                const data = await res.json();
                
                const signalBox = document.getElementById('signal');
                signalBox.innerText = data.signal;
                signalBox.className = 'signal-box ' + data.signal;
                
                document.getElementById('rsi').innerText = data.rsi;
                document.getElementById('confidence').innerText = data.confidence + ' / 10';
            } catch (e) { console.error(e); }
        }

        function changeMarket() {
            const market = document.getElementById('marketSelect').value;
            document.getElementById('signal').innerText = 'FETCHING...';
            document.getElementById('signal').className = 'signal-box WAITING';
            loadChart(marketTvMap[market]);
            fetchSignal();
        }

        window.onload = () => {
            fetchSignal();
            startTimer();
            loadChart(marketTvMap["EURUSD"]);
        };
    </script>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>QUNTEAM AI</h1>
            <p style="color: #8b949e; font-size: 12px; margin-top:0; margin-bottom:15px;">All Markets 1M Pro Dashboard</p>
            
            <select id="marketSelect" class="select-box" onchange="changeMarket()">
                <optgroup label="Forex Pairs">
                    <option value="EURUSD">EUR / USD</option>
                    <option value="GBPUSD">GBP / USD</option>
                    <option value="USDJPY">USD / JPY</option>
                    <option value="AUDUSD">AUD / USD</option>
                    <option value="USDCAD">USD / CAD</option>
                    <option value="USDCHF">USD / CHF</option>
                    <option value="NZDUSD">NZD / USD</option>
                </optgroup>
                <optgroup label="Crypto Pairs (24/7)">
                    <option value="BTCUSDT">BTC / USDT</option>
                    <option value="ETHUSDT">ETH / USDT</option>
                </optgroup>
            </select>

            <div id="timer" class="timer-box">Candle Close In: --s</div>
            <div id="signal" class="signal-box WAITING">LOADING...</div>
            
            <div class="stat-row">
                <span class="label">RSI (14)</span>
                <span id="rsi" class="value">--</span>
            </div>
            <div class="stat-row">
                <span class="label">Confidence</span>
                <span id="confidence" class="value">--</span>
            </div>
        </div>

        <div class="chart-card">
            <div id="tv-chart-container" style="height: 100%; width: 100%;"></div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/signals/<market>', methods=['GET'])
def get_signal(market):
    if market not in MARKETS:
        return jsonify({"signal": "WAITING", "confidence": 5, "rsi": 50})
        
    info = MARKETS[market]
    prices = fetch_market_data(market, info["type"])
    if prices.empty:
        return jsonify({"signal": "WAITING", "confidence": 5, "rsi": 50})

    rsi = calculate_rsi(prices)
    ma_short = prices.rolling(window=9).mean().iloc[-1]
    current_price = prices.iloc[-1]

    if rsi < 32:
        signal = "CALL"
        confidence = 8
    elif rsi > 68:
        signal = "PUT"
        confidence = 8
    else:
        if current_price > ma_short:
            signal = "CALL"
            confidence = 6
        else:
            signal = "PUT"
            confidence = 6

    return jsonify({
        "signal": signal,
        "confidence": int(confidence),
        "rsi": round(float(rsi), 2)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
