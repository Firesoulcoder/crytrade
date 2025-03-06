import requests
import pandas as pd
import time

# Binance API function to get historical prices
def get_historical_klines(symbol, interval, limit=100, retries=3, delay=3):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}

    for attempt in range(retries):
        response = requests.get(url, params=params)
        if response.status_code == 200:
            try:
                data = response.json()
                if not data:
                    print(f"Warning: No data received for {symbol} on {interval} timeframe.")
                    return None
                # Convert to OHLC format
                return [[float(entry[1]), float(entry[2]), float(entry[3]), float(entry[4])] for entry in data]  # OHLC
            except Exception as e:
                print(f"Error decoding JSON response for {symbol} from Binance API: {e}")
                return None
        else:
            print(f"Error fetching data for {symbol} (Attempt {attempt+1}/{retries}): {response.status_code}")
            time.sleep(delay)
    return None

# Calculate RSI (Relative Strength Index)
def calculate_rsi(prices, period=14):
    if len(prices) < period:
        return None
    delta = pd.Series(prices).diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else None

# Calculate Stochastic RSI
def calculate_stochrsi(prices, period=14, smoothK=3, smoothD=3):
    if len(prices) < period:
        return None, None
    rsi_series = pd.Series([calculate_rsi(prices[:i+1], period) for i in range(len(prices))])
    min_rsi = rsi_series.rolling(window=period).min()
    max_rsi = rsi_series.rolling(window=period).max()
    stochrsi = (rsi_series - min_rsi) / (max_rsi - min_rsi)
    stochrsi_k = stochrsi.rolling(window=smoothK).mean()
    stochrsi_d = stochrsi_k.rolling(window=smoothD).mean()
    return round(stochrsi_k.iloc[-1], 2), round(stochrsi_d.iloc[-1], 2)

# Calculate ATR (Average True Range)
def calculate_atr(prices, period=14):
    if len(prices) < period:
        return None
    high_prices = pd.Series([entry[1] for entry in prices])
    low_prices = pd.Series([entry[2] for entry in prices])
    close_prices = pd.Series([entry[3] for entry in prices])
    high_low = high_prices - low_prices
    high_close = (high_prices - close_prices.shift()).abs()
    low_close = (low_prices - close_prices.shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return round(atr.iloc[-1], 5) if not atr.empty else None

# Convert indicators to trade signals
def get_trade_signal(rsi, stochrsi_k, stochrsi_d, atr):
    # RSI Signal
    if rsi > 70:
        rsi_signal = "Overbought - Strong Sell"
    elif rsi < 30:
        rsi_signal = "Oversold - Strong Buy"
    else:
        rsi_signal = "Neutral"
    
    # StochRSI Signal
    if stochrsi_k > 0.8:
        stochrsi_signal = "Strong Sell"
    elif stochrsi_k < 0.2:
        stochrsi_signal = "Strong Buy"
    elif stochrsi_k > stochrsi_d:
        stochrsi_signal = "Buy"
    else:
        stochrsi_signal = "Sell"
    
    # ATR Volatility Signal
    if atr == 0:
        volatility_signal = "Sideways (Low volatility)"
    elif atr > 0.002:
        volatility_signal = "High Volatility"
    else:
        volatility_signal = "Stable Market"
    
    # Estimated Hold Time
    if "Buy" in rsi_signal or "Buy" in stochrsi_signal:
        estimated_hold_time = "Hold for 1-3 days"
    elif "Sell" in rsi_signal or "Sell" in stochrsi_signal:
        estimated_hold_time = "Exit within hours"
    else:
        estimated_hold_time = "Wait for a clear signal"

    return {
        "RSI Signal": rsi_signal,
        "StochRSI Signal": stochrsi_signal,
        "ATR Signal": volatility_signal,
        "Estimated Time to Hold": estimated_hold_time
    }

# Analyze multiple timeframes and determine the best one
def analyze_best_timeframe(crypto):
    timeframes = ["15m", "1h", "4h", "1d"]
    best_timeframe = None
    best_signal_strength = -1  # Higher is better

    results = {}
    
    for timeframe in timeframes:
        prices = get_historical_klines(crypto, timeframe)
        if not prices:
            continue
        
        closing_prices = [entry[3] for entry in prices]
        rsi = calculate_rsi(closing_prices)
        stochrsi_k, stochrsi_d = calculate_stochrsi(closing_prices)
        atr = calculate_atr(prices)

        if rsi is None or stochrsi_k is None or atr is None:
            continue

        signals = get_trade_signal(rsi, stochrsi_k, stochrsi_d, atr)
        results[timeframe] = signals

        # Determine strength of the signal
        signal_strength = 0
        if "Strong Buy" in signals["RSI Signal"] or "Strong Buy" in signals["StochRSI Signal"]:
            signal_strength += 2
        if "Buy" in signals["RSI Signal"] or "Buy" in signals["StochRSI Signal"]:
            signal_strength += 1
        if "Strong Sell" in signals["RSI Signal"] or "Strong Sell" in signals["StochRSI Signal"]:
            signal_strength -= 2
        if "Sell" in signals["RSI Signal"] or "Sell" in signals["StochRSI Signal"]:
            signal_strength -= 1

        # Choose the best timeframe
        if signal_strength > best_signal_strength:
            best_signal_strength = signal_strength
            best_timeframe = timeframe

    return best_timeframe, results

# Main function to analyze a cryptocurrency
def check_crypto_rsi(crypto_pair):
    print(f"Analyzing {crypto_pair.upper()}USDT across multiple timeframes...")
    best_timeframe, analysis_results = analyze_best_timeframe(f"{crypto_pair.upper()}USDT")

    if best_timeframe:
        print(f"\nBest Timeframe: {best_timeframe}")
        for indicator, value in analysis_results[best_timeframe].items():
            print(f"{indicator}: {value}")
    else:
        print("No strong signal detected.")

if __name__ == "__main__":
    crypto_pair = input("Enter the cryptocurrency name (e.g., BTC, ETH, ONE): ").lower()
    check_crypto_rsi(crypto_pair)
