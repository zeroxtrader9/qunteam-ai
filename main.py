from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

# Pocket Option top Forex pairs mapping for backend & TradingView
FOREX_MARKETS = {
    "EURUSD": {"tv_symbol": "FX:EURUSD", "label": "EUR / USD"},
    "GBPUSD": {"tv_symbol": "FX:GBPUSD", "label": "GBP / USD"},
    "USDJPY": {"tv_symbol": "FX:USDJPY", "label": "USD / JPY"},
    "AUDUSD": {"tv_symbol": "FX:AUDUSD", "label": "AUD / USD"},
    "USDCAD": {"tv_symbol": "FX:USDCAD", "label": "USD / CAD"},
    "USDCHF": {"tv_symbol": "FX:USDCHF", "label": "USD / CHF"},
    "NZDUSD": {"tv_symbol": "FX:NZDUSD", "label": "NZD / USD"},
    "EURGBP": {"tv_symbol": "FX:EURGBP", "label": "EUR / GBP"},
    "EURJPY": {"tv_symbol": "FX:EURJPY", "label": "EUR / JPY"}
}

def fetch_forex_data(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}=X?interval=1m&range=1d"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers).json()
        closes = res['chart']['result'][0]['indicators']['quote'][0]['close']
        closes = [c for c in closes if c is not None][-50:]
        return pd.Series(closes)
    except Exception as e:
        print(f"Data fetch error for {symbol}:", e)
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
    <title>QUNTEAM AI - Forex & Live Charts</title>
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
            padding: 20px;
            box-sizing: border-box;
        }
        .container {
            display: flex;
            flex-direction: row;
            gap: 20px;
            max-width: 1000px;
            width: 100%;
        }
        .card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            flex: 1;
            max-width: 360px;
        }
        .chart-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            flex: 2;
            height: 450px;
        }
        h1 { font-size: 24px; margin-bottom: 5px; color: #58a6ff; }
        .select-box {
            background-color: #21262d;
            color: #c9d1d9;
            border: 1px solid #30363d;
            padding: 10px;
            border-radius: 6px;
            width: 100%;
            font-size: 16px;
            margin-bottom: 20px;
            outline: none;
            cursor: pointer;
        }
        .signal-box {
            font-size: 36px;
            font-weight: bold;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            letter-spacing: 2px;
        }
        .CALL { background-color: rgba(46, 160, 67, 0.15); color: #3fb950; border: 1px solid #2ea043; }
        .PUT { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
        .WAITING { background-color: rgba(139, 148, 158, 0.15); color: #8b949e; border: 1px solid #30363d; }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #21262d;
        }
        .stat-row:last-child { border-bottom: none; }
        .label { color: #8b949e; }
        .value { font-weight: 600; color: #f0f6fc; }
        .refresh-text { font-size: 11px; color: #8b949e; margin-top: 20px; }
        
        @media (max-width: 768px) {
            .container { flex-direction: column; align-items: center; }
            .card, .chart-card { width: 100%; max-width: 100%; }
            .chart-card { height: 350px; }
        }
    </style>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script>
        let autoRefresh;
        let tvWidget;

        const marketTvMap = {
            "EURUSD": "FX:EURUSD",
            "GBPUSD": "FX:GBPUSD",
            "USDJPY": "FX:USDJPY",
            "AUDUSD": "FX:AUDUSD",
            "USDCAD": "FX:USDCAD",
            "USDCHF": "FX:USDCHF",
            "NZDUSD": "FX:NZDUSD",
            "EURGBP": "FX:EURGBP",
            "EURJPY": "FX:EURJPY"
        };

        function loadTradingViewChart(symbol) {
            tvWidget = new TradingView.widget({
                "width": "100%",
                "height": "100%",
                "symbol": symbol,
                "interval": "1",
                "timezone": "Etc/UTC",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "enable_publishing": false,
                "hide_side_toolbar": false,
                "allow_symbol_change": false,
                "container_id": "tv-chart-container"
            });
        }
        
        async function fetchSignal() {
            const market = document.getElementById('marketSelect').value;
            const signalBox = document.getElementById('signal');
            
            try {
                const res = await fetch('/api/signals/' + market);
                const data = await res.json();
                
                signalBox.innerText = data.signal;
                signalBox.className = 'signal-box ' + data.signal;
                
                document.getElementById('rsi').innerText = data.rsi;
                document.getElementById('confidence').innerText = data.confidence + ' / 10';
            } catch (e) {
                console.error("Error updating dashboard:", e);
            }
        }

        function onMarketChange() {
            const market = document.getElementById('marketSelect').value;
            document.getElementById('signal').innerText = 'FETCHING...';
            document.getElementById('signal').className = 'signal-box WAITING';
            
            // Reload Chart for new market
            loadTradingViewChart(marketTvMap[market]);
            fetchSignal();
        }

        window.onload = () => {
            fetchSignal();
            loadTradingViewChart(marketTvMap["EURUSD"]);
            autoRefresh = setInterval(fetchSignal, 5000);
        };
    </script>
</head>
<body>
    <div class="container">
        <!-- Left Side: Control & Signals -->
        <div class="card">
            <h1>QUNTEAM AI</h1>
            <p style="color: #8b949e; font-size: 13px; margin-top:0; margin-bottom:15px;">Pocket Option Forex Pro</p>
            
            <select id="marketSelect" class="select-box" onchange="onMarketChange()">
                <option value="EURUSD">EUR / USD</option>
                <option value="GBPUSD">GBP / USD</option>
                <option value="USDJPY">USD / JPY</option>
                <option value="AUDUSD">AUD / USD</option>
                <option value="USDCAD">USD / CAD</option>
                <option value="USDCHF">USD / CHF</option>
                <option value="NZDUSD">NZD / USD</option>
                <option value="EURGBP">EUR / GBP</option>
                <option value="EURJPY">EUR / JPY</option>
            </select>

            <div id="signal" class="signal-box WAITING">LOADING...</div>
            
            <div class="stat-row">
                <span class="label">RSI (14) Indicator</span>
                <span id="rsi" class="value">--</span>
            </div>
            <div class="stat-row">
                <span class="label">Signal Confidence</span>
                <span id="confidence" class="value">--</span>
            </div>
            <div class="refresh-text">Auto-refreshing live data every 5 seconds...</div>
        </div>

        <!-- Right Side: Live TradingView Chart -->
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
    if market not in FOREX_MARKETS:
        return jsonify({"signal": "WAITING", "confidence": 5, "rsi": 50})
        
    prices = fetch_forex_data(market)
    if prices.empty:
        return jsonify({"signal": "WAITING", "confidence": 5, "rsi": 50})

    rsi = calculate_rsi(prices)
    ma_short = prices.rolling(window=9).mean().iloc[-1]
    ma_long = prices.rolling(window=21).mean().iloc[-1]
    current_price = prices.iloc[-1]

    if rsi < 32 and current_price > ma_short:
        signal = "CALL"
        confidence = 8
    elif rsi > 68 and current_price < ma_short:
        signal = "PUT"
        confidence = 8
    else:
        if ma_short > ma_long:
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
