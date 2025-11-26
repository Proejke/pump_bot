import ccxt, time, requests, os, io
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ─────── Настройки (можно менять под себя) ───────
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MIN_CHANGE = 9.0        # минимальный % роста за 50 минут
MIN_VOLUME_USD = 800000 # минимальный объём в $
MIN_PRICE = 0.0002      # минимальная цена
RSI_PERIOD = 14
RSI_OVERBOUGHT = 68     # сигнал только если RSI < 68 (не перегрет)
REPEAT_DELAY = 3600     # не слать повторно по одной монете раньше часа

# ─────── Не трогай ниже ───────
ex = ccxt.mexc()
sent_times = {}  # {symbol: timestamp последнего сигнала}

def rsi(prices, period=14):
    deltas = np.diff(prices)
    up = deltas.clip(min=0)
    down = -deltas.clip(max=0)
    ma_up = np.mean(up[-period:])
    ma_down = np.mean(down[-period:])
    if ma_down == 0: return 0
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

def draw_chart(ohlcv):
    img = Image.new('RGB', (800, 400), (18, 18, 28))
    draw = ImageDraw.Draw(img)
    closes = [x[4] for x in ohlcv]
    high = max(closes)
    low = min(closes)
    width = 800 // len(ohlcv)
    for i, (t, o, h, l, c, v) in enumerate(ohlcv):
        x = i * width
        h_y = int(350 - (h - low) / (high - low + 1e-8) * 330)
        l_y = int(350 - (l - low) / (high - low + 1e-8) * 330)
        c_y = int(350 - (c - low) / (high - low + 1e-8) * 330)
        o_y = int(350 - (o - low) / (high - low + 1e-8) * 330)
        color = (0, 255, 140) if c >= o else (255, 50, 50)
        draw.line([(x + width//2, h_y), (x + width//2, l_y)], fill=color, width=1)
        draw.rectangle([x+5, min(o_y,c_y), x+width-5, max(o_y,c_y)], fill=color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def send_photo(photo_bytes, caption):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": ("chart.png", photo_bytes, "image/png")}
        )
    except: pass

print("Запущен PRO-сканер с RSI + графиком (2025)")

while True:
    try:
        markets = ex.load_markets()
        symbols = [s for s in markets.keys() if s.endswith('/USDT') and markets[s]['spot']]
        
        for symbol in symbols:
            now = time.time()
            if symbol in sent_times and now - sent_times[symbol] < REPEAT_DELAY:
                continue
                
            try:
                ohlcv = ex.fetch_ohlcv(symbol, '5m', limit=50)
                if len(ohlcv) < RSI_PERIOD + 10: continue
                closes = [x[4] for x in ohlcv]
                change = (closes[-1] - closes[-10]) / closes[-10] * 100
                volume_usd = sum(x[5] * x[4] for x in ohlcv[-20:])
                price = closes[-1]
                current_rsi = rsi(closes[-RSI_PERIOD-10:])

                if (change >= MIN_CHANGE and 
                    volume_usd >= MIN_VOLUME_USD and 
                    price >= MIN_PRICE and 
                    current_rsi <= RSI_OVERBOUGHT):
                    
                    coin = symbol.split('/')[0].replace('1000', '')
                    msg = f"""#PUMP #{coin}
+{change:.2f}% за последние 50 мин
Цена: <code>${price:.6f}</code>
Объём 20 свечей: <b>${volume_usd/1e6:.2f}M</b>
RSI(14): <b>{current_rsi:.1f}</b>
MEXC → https://mexc.com/exchange/{symbol.replace('/', '_')}"""

                    chart = draw_chart(ohlcv[-40:])
                    send_photo(chart, msg)
                    sent_times[symbol] = now
                    print(f"Сигнал → {coin} +{change:.1f}% | RSI {current_rsi:.1f}")
                    time.sleep(3)
            except: continue
                
        print(f"{datetime.now().strftime('%H:%M:%S')} — цикл ок, сплю 100 сек")
        time.sleep(100)
        
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(30)
