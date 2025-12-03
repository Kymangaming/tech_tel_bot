import requests
import time
import numpy as np

# ====== تنظیمات ======
TELEGRAM_TOKEN = "5450700098:AAHa3d5F-q9hmfPYdj_cEioEHi2WoYEKMLU"
CHAT_ID = "1134506541"
CRYPTOS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
INTERVAL = 300  # هر ۵ دقیقه

# پارامترهای TP/SL پویا
TP_MULTIPLIER = [1.02, 1.05]  # TP1 و TP2 برای خرید
SL_MULTIPLIER = 0.98           # SL برای خرید
# برای فروش، TP و SL معکوس خواهند شد

# ====== گرفتن داده کندل ======
def get_binance_candles(symbol, interval="5m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        closes = [float(c[4]) for c in data if len(c) > 4]
        return closes
    except Exception as e:
        print(f"⚠️ خطا در دریافت داده‌های {symbol}: {e}")
        return []

# ====== EMA ======
def ema(prices, period):
    prices = np.array(prices)
    return prices[-period:].mean() if len(prices) >= period else None

# ====== RSI ======
def rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    deltas = np.diff(prices[-(period+1):])
    ups = deltas[deltas > 0].sum() / period
    downs = -deltas[deltas < 0].sum() / period
    rs = ups / downs if downs != 0 else 0
    return 100 - (100 / (1 + rs))

# ====== MACD ======
def macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow + signal:
        return None, None
    ema_fast = np.mean(prices[-fast:])
    ema_slow = np.mean(prices[-slow:])
    macd_line = ema_fast - ema_slow
    signal_line = np.mean(prices[-signal:])
    return macd_line, signal_line

# ====== تحلیل حرفه‌ای ======
def analyze_signal(closes):
    if len(closes) < 26:
        return None
    current_price = closes[-1]

    ema_short = ema(closes, 7)
    ema_long = ema(closes, 25)
    rsi_val = rsi(closes)
    macd_val, signal_val = macd(closes)

    if None in [ema_short, ema_long, rsi_val, macd_val, signal_val]:
        return None

    # قوانین سیگنال:
    buy_signal = ema_short > ema_long and rsi_val < 70 and macd_val > signal_val
    sell_signal = ema_short < ema_long and rsi_val > 30 and macd_val < signal_val

    if buy_signal:
        tp1 = current_price * TP_MULTIPLIER[0]
        tp2 = current_price * TP_MULTIPLIER[1]
        sl = current_price * SL_MULTIPLIER
        return {"signal": "📈 خرید", "price": current_price, "tp1": tp1, "tp2": tp2, "sl": sl}
    elif sell_signal:
        tp1 = current_price * (2 - TP_MULTIPLIER[0])  # معکوس برای فروش
        tp2 = current_price * (2 - TP_MULTIPLIER[1])
        sl = current_price * (2 - SL_MULTIPLIER)
        return {"signal": "📉 فروش", "price": current_price, "tp1": tp1, "tp2": tp2, "sl": sl}
    else:
        return None

# ====== ارسال پیام تلگرام ======
def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code == 200:
            print("✅ پیام تلگرام ارسال شد.")
        else:
            print(f"⚠️ خطا در ارسال پیام: {r.text}")
    except Exception as e:
        print(f"⚠️ خطا در اتصال به تلگرام: {e}")

# ====== حلقه اصلی ======
def main():
    while True:
        all_signals = []
        for crypto in CRYPTOS:
            closes = get_binance_candles(crypto, "5m")
            analysis = analyze_signal(closes)
            if analysis:
                msg = (
                    f"{crypto} | {analysis['signal']}\n"
                    f"ورود: {analysis['price']:.2f}\n"
                    f"TP1: {analysis['tp1']:.2f}\n"
                    f"TP2: {analysis['tp2']:.2f}\n"
                    f"SL: {analysis['sl']:.2f}"
                )
            else:
                msg = f"{crypto}: ⚠️ اطلاعات کافی یا روند خنثی"
            all_signals.append(msg)

        final_msg = "📊 سیگنال‌های حرفه‌ای رمزارز:\n\n" + "\n\n".join(all_signals)
        send_telegram_message(final_msg)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] پیام ارسال شد.")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
