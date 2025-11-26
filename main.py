import ccxt, time, requests, os, io
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

mexc = ccxt.mexc()
bybit = ccxt.bybit({'options': {'defaultType': 'swap'}})
sent = set()  # защита от спама

def has_futures_anywhere(base):
    try:
        # MEXC perpetual
        if any(base + 'USDT' in s for s in mexc.load_markets().keys() if 'PERP' in s):
            return 'mexc'
        # ByBit perpetual
        if base + '/USDT:USDT' in bybit.load_markets():
            return 'bybit'
    except:
        pass
    return False

def draw_chart(ohlcv):
    img = Image.new('RGB', (1200, 675), (18, 18, 28))
    draw = ImageDraw.Draw(img)
    closes = [c[4] for c in ohlcv]
    high, low = max(closes), min(closes)
    width = 1200 // len(ohlcv)
    for i, (t, o, h, l, c, v) in enumerate(ohlcv):
        x = i * width + 30
        hy = int(580 - (h - low)/(high-low+1e-9)*540)
        ly = int(580 - (l - low)/(high-low+1e-9)*540)
        oy = int(580 - (o - low)/(high-low+1e-9)*540)
        cy = int(580 - (c - low)/(high-low+1e-9)*540)
        color = (255,70,70) if c < o else (0,255,140)
        draw.line([(x+width//2, hy), (x+width//2, ly)], fill=color, width=3)
        draw.rectangle([x+10, min(oy,cy), x+width-10, max(oy,cy)], fill=color)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return buf

print("ШАОРТ-МАШИНА 2025 — 8–25 сигналов в час, только с фьючерсами")

while True:
    try:
        for symbol in [s for s in mexc.load_markets() if s.endswith('/USDT') and mexc.markets[s]['spot']]:
            base = symbol.split('/')[0].replace('1000','')
            if symbol in sent: continue

            # Проверка фьючерсов (MEXC или ByBit)
            platform = has_futures_anywhere(base)
            if not platform: 
                continue

            try:
                ohlcv = mexc.fetch_ohlcv(symbol, '5m', limit=50)
                if len(ohlcv) < 35: continue

                closes = np.array([x[4] for x in ohlcv])
                price = closes[-1]
                change_20m = (price / closes[-5] - 1) * 100   # 20 мин
                change_45m = (price / closes[-10] - 1) * 100  # 45 мин
                rsi = 100 - 100/(1 + np.mean(np.diff(closes[-15:]).clip(min=0)) / 
                                   (abs(np.mean(np.diff(closes[-15:]).clip(max=0)))+1e-8))
                volume_spike = sum(x[5] for x in ohlcv[-8:]) / max(1, sum(x[5] for x in ohlcv[-25:-8]))

                if (price >= 0.00015 and
                    rsi >= 78 and
                    price >= max(closes[-15:]) * 0.995 and   # почти максимум за час
                    volume_spike >= 4 and
                    (change_20m >= 9 or change_45m >= 14)):

                    entry = price
                    sl = round(price * 1.07, 8)
                    tp1 = round(price * 0.84, 8)
                    tp2 = round(price * 0.70, 8)
                    tp3 = round(price * 0.52, 8)

                    platform_name = "MEXC" if platform == 'mexc' else "ByBit"
                    caption = f"""#ШОРТ {base} НА ПИКЕ
Вход: <code>{entry:.8f}</code>
SL: <code>{sl}</code> (+7%)
TP1: <code>{tp1}</code> (-16%)
TP2: <code>{tp2}</code> (-30%)
TP3: <code>{tp3}</code> (-48%)
RSI {rsi:.1f}% ×{volume_spike:.1f}
ФЬЮЧЕРСЫ: {platform_name}"""

                    chart = draw_chart(ohlcv[-35:])
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                                data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                                files={"photo": ("short.png", chart, "image/png")})
                    sent.add(symbol)
                    print(f"ЧАСТЫЙ ШОРТ → {base} +{max(change_20m,change_45m):.1f}% | RSI {rsi:.1f}")
                    time.sleep(2)

            except: continue

        print(f"{datetime.now().strftime('%H:%M:%S')} — цикл (8–25 сигналов/час)")
        time.sleep(48)   # проверка каждые 48 сек = максимальная частота

    except Exception as e:
        print("Ошибка:", e)
        time.sleep(20)
