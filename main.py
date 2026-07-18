from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

def fetch_market_data(symbol):
    formatted_symbol = symbol.replace("BINANCE:", "")
    url = f"https://api.binance.com/api/v3/klines?symbol={formatted_symbol}&interval=1m&limit=50"
    try:
        response = requests.get(url).json()
        if isinstance(response, dict) and "code" in response:
            return pd.Series([])
        closes = [float(candle[4]) for candle in response]
        return pd.Series(closes)
    except Exception as e:
        print("Data fetch error:", e)
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

# Front-end HTML Dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QUNTEAM AI - Signals Dashboard</title>
    <style>
        body {
            background-color: #0d1117;
            color: #c9d1d9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            width: 350px;
        }
        h1 { font-size: 24px; margin-bottom: 5px; color: #58a6ff; }
        .market { color: #8b949e; margin-bottom: 25px; font-size: 14px; letter-spacing: 1px; }
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
            padding: 10px 0;
            border-bottom: 1px solid #21262d;
        }
        .stat-row:last-child { border-bottom: none; }
        .label { color: #8b949e; }
        .value { font-weight: 600; color: #f0f6fc; }
        .refresh-text { font-size: 11px; color: #8b949e; margin-top: 20px; }
    </style>
    <script>
        async function fetchSignal() {
            try {
                const res = await fetch('/api/signals/BTCUSDT');
                const data = await res.json();
                
                const signalBox = document.getElementById('signal');
                signalBox.innerText = data.signal;
                signalBox.className = 'signal-box ' + data.signal;
                
                document.getElementById('rsi').innerText = data.rsi;
                document.getElementById('confidence').innerText = data.confidence + ' / 10';
            } catch (e) {
                console.error("Error updating dashboard:", e);
            }
        }
        setInterval(fetchSignal, 5000);
        window.onload = fetchSignal;
    </script>
</head>
<body>
    <div class="card">
        <h1>QUNTEAM AI</h1>
        <div class="market">BTCUSDT (1M INTERVAL)</div>
        <div id="signal" class="signal-box WAITING">LOADING...</div>
        <div class="stat-row">
            <span class="label">RSI Indicator</span>
            <span id="rsi" class="value">--</span>
        </div>
        <div class="stat-row">
            <span class="label">Confidence Score</span>
            <span id="confidence" class="value">--</span>
        </div>
        <div class="refresh-text">Auto-refreshing every 5 seconds...</div>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/signals/<market>', methods=['GET'])
def get_signal(market):
    prices = fetch_market_data(market)
    if prices.empty:
        return jsonify({"signal": "WAITING", "confidence": 5, "rsi": 50})

    rsi = calculate_rsi(prices)
    ma_short = prices.rolling(window=9).mean().iloc[-1]
    ma_long = prices.rolling(window=21).mean().iloc[-1]
    current_price = prices.iloc[-1]

    if rsi < 35 and current_price > ma_short:
        signal = "CALL"
        confidence = 8
    elif rsi > 65 and current_price < ma_short:
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
