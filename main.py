import ccxt, time, requests, os, io
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ex = ccxt.mexc()
sent = set()

def draw_chart(ohlcv):
    img = Image.new('RGB', (1200, 675), (18, 18, 28))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 36)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 28)
    except:
        font = ImageFont.load_default()
        font_small = font

    closes = [c[4] for c in ohlcv]
    high, low = max(closes), min(closes)
    width = 1200 // len(ohlcv)

    for i, (t, o, h, l, c, v) in enumerate(ohlcv):
        x = i * width + 30
        hy = int(580 - (h - low) / (high - low + 1e-9) * 540)
        ly = int(580 - (l - low) / (high - low + 1e-9) * 540)
        oy = int(580 - (o - low) / (high - low + 1e-9) * 540)
        cy = int(580 - (c - low) / (high - low + 1e-9) * 540)
        color = (0, 255, 140) if c >= o else (255, 70, 70)
        draw.line([(x + width//2, hy), (x + width//2, ly)], fill=color, width=3)
        draw.rectangle([x+10, min(oy,cy), x+width-10, max(oy,cy)], fill=color)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

print("Запущен сканер как у Дмитрия — с графиком и RSI")

while True:
    try:
        markets = ex.load_markets()
        for symbol in [s for s in markets if s.endswith('/USDT') and markets[s]['spot']]:
            if symbol in sent: continue
            try:
                ohlcv = ex.fetch_ohlcv(symbol, '5m', limit=40)
                if len(ohlcv) < 35: continue
                closes = [x[4] for x in ohlcv]
                change = (closes[-1] - closes[-10]) / closes[-10] * 100
                price = closes[-1]
                volume_usd = sum(x[5] * x[4] for x in ohlcv[-12:])

                # RSI
                deltas = np.diff(closes[-15:])
                up = deltas.clip(min=0)
                down = -deltas.clip(max=0)
                ma_up = np.mean(up[-14:]) if len(up) >= 14 else 0
                ma_down = np.mean(down[-14:]) if len(down) >= 14 else 0
                rsi = 100 - (100 / (1 + ma_up/ma_down)) if ma_down != 0 else 50

                if change >= 10 and volume_usd >= 900000 and price >= 0.0002 and rsi <= 75:
                    coin = symbol.split('/')[0].replace('1000', '')
                    caption = f"""#МОНЕТА: {coin} FAST
Pump: {change:.2f}%
Trade: MEXC  ByBit
RSI: {rsi:.1f}%"""

                    chart = draw_chart(ohlcv[-35:])
                    requests.post(
                        f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                        data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                        files={"photo": ("chart.png", chart, "image/png")}
                    )
                    sent.add(symbol)
                    print(f"Сигнал как у Дмитрия → {coin} +{change:.1f}% | RSI {rsi:.1f}")
                    time.sleep(4)
            except: continue

        print(f"{datetime.now().strftime('%H:%M:%S')} — цикл ок")
        time.sleep(85)

    except Exception as e:
        print("Ошибка:", e)
        time.sleep(30)
