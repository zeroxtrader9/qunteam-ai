from flask import Flask, jsonify
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

@app.route('/get-signal/<market>', methods=['GET'])
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
