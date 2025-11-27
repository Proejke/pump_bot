import ccxt, time, requests, os, io
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

mexc = ccxt.mexc()
bybit = ccxt.bybit({'options': {'defaultType': 'swap'}})
sent = set()
last_reset = time.time()

print("ШОРТ-КИЛЛЕР AGGRESSIVE 2025 — ЗАПУЩЕН")

while True:
    try:
        # Сброс sent каждые 6 часов
        if time.time() - last_reset > 6*3600:
            sent.clear()
            last_reset = time.time()

        markets = mexc.load_markets()
        for symbol in [s for s in markets if s.endswith('/USDT') and markets[s]['spot']]:
            base = symbol.split('/')[0].replace('1000', '')
            if symbol in sent: continue

            # Фьючерсы?
            has_fut = False
            try:
                if any('USDT' in s and markets[s].get('swap') for s in markets if base in s):
                    has_fut = True
                elif base + '/USDT:USDT' in bybit.load_markets():
                    has_fut = True
            except: pass
            if not has_fut: continue

            ohlcv = mexc.fetch_ohlcv(symbol, '5m', limit=60)
            if len(ohlcv) < 50: continue

            closes = np.array([c[4] for c in ohlcv])
            price = closes[-1]
            if price < 0.0001: continue

            change_15m = (price / closes[-4] - 1) * 100 if len(closes) > 4 else 0
            change_45m = (price / closes[-10] - 1) * 100 if len(closes) > 10 else 0

            delta = np.diff(closes[-15:])
            gain = np.mean(delta.clip(min=0))
            loss = abs(np.mean(delta.clip(max=0)))
            rsi = 100 - 100 / (1 + gain / (loss + 1e-8)) if loss != 0 else 100

            volume_spike = sum(x[5] for x in ohlcv[-6:]) / max(1, sum(x[5] for x in ohlcv[-25:-6]))

            # АГРЕССИВНЫЕ ФИЛЬТРЫ
            if (rsi >= 74 and 
                volume_spike >= 2.9 and 
                price >= max(closes[-12:]) * 0.97 and
                (change_15m >= 7 or change_45m >= 12)):

                # === РИСУЕМ ГРАФИК ===
                img = Image.new('RGB', (1200, 720), (18,18,28))
                draw = ImageDraw.Draw(img)
                try: font = ImageFont.truetype("arial.ttf", 28)
                except: font = ImageFont.load_default()

                high, low = max(closes), min(closes)
                width = 1200 // 45
                for i, c in enumerate(ohlcv[-45:]):
                    x = i * width + 40
                    o, h, l, cl = c[1], c[2], c[3], c[4]
                    hy = int(650 - (h-low)/(high-low+1e-9)*600)
                    ly = int(650 - (l-low)/(high-low+1e-9)*600)
                    oy = int(650 - (o-low)/(high-low+1e-9)*600)
                    cy = int(650 - (cl-low)/(high-low+1e-9)*600)
                    color = (0,255,140) if cl >= o else (255,70,70)
                    draw.line([(x+width//2, hy), (x+width//2, ly)], fill=color, width=3)
                    draw.rectangle([x+8, min(oy,cy), x+width-8, max(oy,cy)], fill=color)

                # Уровни
                sl = round(price * 1.07, 8)
                tp1 = round(price * 0.88, 8)
                tp2 = round(price * 0.75, 8)
                tp3 = round(price * 0.60, 8)

                draw.text((50, 50), f"ШОРТ {base}", fill=(255,100,100), font=font)
                draw.text((50, 100), f"Вход: {price:.8f}", fill=(255,255,255), font=font)
                draw.text((50, 150), f"SL: {sl} (+7%)", fill=(255,255,255), font=font)
                draw.text((50, 200), f"TP1: {tp1}", fill=(0,255,140), font=font)
                draw.text((50, 250), f"TP2: {tp2}", fill=(0,255,140), font=font)
                draw.text((50, 300), f"TP3: {tp3}", fill=(0,255,140), font=font)
                draw.text((50, 400), f"RSI {rsi:.1f} ×{volume_spike:.1f}", fill=(100,200,255), font=font)

                buf = io.BytesIO()
                img.save(buf, 'PNG')
                buf.seek(0)

                caption = f"""#ШОРТ {base}
Вход: <code>{price:.8f}</code>
SL: <code>{sl}</code>
TP1: <code>{tp1}</code>  TP2: <code>{tp2}</code>  TP3: <code>{tp3}</code>
RSI {rsi:.1f}% │ ×{volume_spike:.1f}"""

                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                            files={"photo": ("short.png", buf)})

                sent.add(symbol)
                print(f"СИГНАЛ → {base} {price:.6f}")

        print(f"{datetime.now().strftime('%H:%M:%S')} — сканирую агрессивно")
        time.sleep(35)

    except Exception as e:
        print("Ошибка:", e)
        time.sleep(15)
