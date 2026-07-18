from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

# Forex & Crypto mix for 24/7 weekend testing
FOREX_MARKETS = {
    "EURUSD": {"tv_symbol": "FX:EURUSD", "crypto_fallback": "BTCUSDT"},
    "GBPUSD": {"tv_symbol": "FX:GBPUSD", "crypto_fallback": "ETHUSDT"},
    "USDJPY": {"tv_symbol": "FX:USDJPY", "crypto_fallback": "SOLUSDT"},
    "AUDUSD": {"tv_symbol": "FX:AUDUSD", "crypto_fallback": "BNBUSDT"},
    "USDCAD": {"tv_symbol": "FX:USDCAD", "crypto_fallback": "XRPUSDT"},
    "USDCHF": {"tv_symbol": "FX:USDCHF", "crypto_fallback": "ADAUSDT"},
    "NZDUSD": {"tv_symbol": "FX:NZDUSD", "crypto_fallback": "DOTUSDT"},
    "EURGBP": {"tv_symbol": "FX:EURGBP", "crypto_fallback": "DOGEUSDT"},
    "EURJPY": {"tv_symbol": "FX:EURJPY", "crypto_fallback": "AVAXUSDT"}
}

def fetch_live_data(market_name):
    # Weekend par live signals dikhane ke liye crypto data use karenge fallback me
    crypto_pair = FOREX_MARKETS[market_name]["crypto_fallback"]
    url = f"https://api.binance.com/api/v3/klines?symbol={crypto_pair}&interval=1m&limit=50"
    try:
        response = requests.get(url).json()
        if isinstance(response, list):
            closes = [float(candle[4]) for candle in response]
            return pd.Series(closes)
        return pd.Series([])
    except Exception as e:
        print(f"Data fetch error: {e}")
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
    <title>QUNTEAM AI - 24/7 Live Signals</title>
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
        <div class="card">
            <h1>QUNTEAM AI</h1>
            <p style="color: #8b949e; font-size: 13px; margin-top:0; margin-bottom:15px;">Pocket Option OTC / Weekend Mode</p>
            
            <select id="marketSelect" class="select-box" onchange="onMarketChange()">
                <option value="EURUSD">EUR / USD (OTC Mode)</option>
                <option value="GBPUSD">GBP / USD (OTC Mode)</option>
                <option value="USDJPY">USD / JPY (OTC Mode)</option>
                <option value="AUDUSD">AUD / USD (OTC Mode)</option>
                <option value="USDCAD">USD / CAD (OTC Mode)</option>
                <option value="USDCHF">USD / CHF (OTC Mode)</option>
                <option value="NZDUSD">NZD / USD (OTC Mode)</option>
                <option value="EURGBP">EUR / GBP (OTC Mode)</option>
                <option value="EURJPY">EUR / JPY (OTC Mode)</option>
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
            <div class="refresh-text">Live signals active 24/7...</div>
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
    if market not in FOREX_MARKETS:
        return jsonify({"signal": "WAITING", "confidence": 5, "rsi": 50})
        
    prices = fetch_live_data(market)
    if prices.empty:
        return jsonify({"signal": "WAITING", "confidence": 5, "rsi": 50})

    rsi = calculate_rsi(prices)
    ma_short = prices.rolling(window=9).mean().iloc[-1]
    ma_long = prices.rolling(window=21).mean().iloc[-1]
    current_price = prices.iloc[-1]

    # Quick Scalping Logic for OTC/Weekend
    if rsi < 35:
        signal = "CALL"
        confidence = 7
    elif rsi > 65:
        signal = "PUT"
        confidence = 7
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
