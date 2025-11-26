import ccxt, time, requests, os, io
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MIN_CHANGE = 8.5
MIN_VOLUME = 700000
MIN_PRICE = 0.00015
RSI_MAX = 70
REPEAT_COOLDOWN = 3600

ex = ccxt.mexc()
last_sent = {}

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    up, down = deltas.copy(), deltas.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    roll_up = np.mean(up[-period:])
    roll_down = abs(np.mean(down[-period:]))
    if roll_down == 0: return 0
    rs = roll_up / roll_down
    return 100 - (100 / (1 + rs))

def draw_candle_chart(ohlcv):
    img = Image.new('RGB', (960, 540), (13, 17, 23))
    draw = ImageDraw.Draw(img)
    closes = [c[4] for c in ohlcv]
    high = max(closes)
    low = min(closes)
    bar_width = 960 // len(ohlcv)
    
    for i, (t, o, h, l, c, v) in enumerate(ohlcv):
        x = i * bar_width + 10
        h_y = int(500 - (h - low) / (high - low + 1e-9) * 460)
        l_y = int(500 - (l - low) / (high - low + 1e-9) * 460)
        o_y = int(500 - (o - low) / (high - low + 1e-9) * 460)
        c_y = int(500 - (c - low) / (high - low + 1e-9) * 460)
        color = (0, 255, 140) if c >= o else (255, 80, 80)
        draw.line([(x + bar_width//2, h_y), (x + bar_width//2, l_y)], fill=color, width=2)
        draw.rectangle([x+8, min(o_y, c_y), x+bar_width-8, max(o_y, c_y)], fill=color, outline=color)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def send_signal(symbol, change, price, volume_usd, rsi_val):
    coin = symbol.split('/')[0].replace('1000', '')
    caption = f"""#МОНЕТА: <b>{coin} FAST</b> 
Pump: <b>{change:.2f}%</b> (0.018998 → {price:.6f})
Trade: MEXC
x100 / 23.8$ / 228.2k$ / 0.0386%
RSI: {rsi_val:.1f}%"""

    try:
        ohlcv = ex.fetch_ohlcv(symbol, '5m', limit=60)
        chart = draw_candle_chart(ohlcv[-50:])
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": ("chart.png", chart, "image/png")}
        )
    except:
        pass

print("Запущен финальный ВИП-сканер 2025")

while True:
    try:
        for symbol in [s for s in ex.load_markets() if s.endswith('/USDT') and ex.markets[s]['spot']]:
            now = time.time()
            if symbol in last_sent and now - last_sent[symbol] < REPEAT_COOLDOWN:
                continue
            try:
                ohlcv = ex.fetch_ohlcv(symbol, '5m', limit=40)
                if len(ohlcv) < 30: continue
                closes = [x[4] for x in ohlcv]
                change = (closes[-1] - closes[-10]) / closes[-10] * 100
                volume_usd = sum(x[5] * x[4] for x in ohlcv[-15:])
                price = closes[-1]
                rsi = calculate_rsi(closes)
                
                if (change >= MIN_CHANGE and volume_usd >= MIN_VOLUME and 
                    price >= MIN_PRICE and rsi <= RSI_MAX):
                    send_signal(symbol, change, price, volume_usd, rsi)
                    last_sent[symbol] = now
                    time.sleep(3)
            except: continue
        print(f"{datetime.now().strftime('%H:%M:%S')} цикл завершён")
        time.sleep(95)
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(30)
