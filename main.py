import ccxt, time, requests, os, io
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ex = ccxt.mexc()
sent = set()  # не спамим одну монету

def draw_chart(ohlcv):
    img = Image.new('RGB', (1200, 675), (18, 18, 28))
    draw = ImageDraw.Draw(img)
    closes = [c[4] for c in ohlcv]
    high, low = max(closes), min(closes)
    width = 1200 // len(ohlcv)
    for i, (t, o, h, l, c, v) in enumerate(ohlcv):
        x = i * width + 30
        hy = int(580 - (h - low) / (high - low + 1e-9) * 540)
        ly = int(580 - (l - low) / (high - low + 1e-9) * 540)
        oy = int(580 - (o - low) / (high - low + 1e-9) * 540)
        cy = int(580 - (c - low) / (high - low + 1e-9) * 540)
        color = (255, 70, 70) if c < o else (0, 255, 140)
        draw.line([(x + width//2, hy), (x + width//2, ly)], fill=color, width=3)
        draw.rectangle([x+10, min(oy,cy), x+width-10, max(oy,cy)], fill=color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

print("ЗАПУЩЕН ШОРТ-КИЛЛЕР 2025 — только жирные дампы шиткоинов")

while True:
    try:
        for symbol in [s for s in ex.load_markets() if s.endswith('/USDT') and ex.markets[s]['spot']]:
            if symbol in sent: continue
            try:
                ohlcv = ex.fetch_ohlcv(symbol, '5m', limit=50)
                if len(ohlcv) < 40: continue
                
                closes = np.array([x[4] for x in ohlcv])
                volumes = np.array([x[5] for x in ohlcv])
                price = closes[-1]

                # === УСЛОВИЯ ДЛЯ ЖИРНОГО ДАМПА ===
                change_15m = (price / closes[-4] - 1) * 100      # +15% за 15 мин
                change_40m = (price / closes[-9] - 1) * 100      # +30% за 40 мин
                rsi = 100 - 100 / (1 + np.mean(np.diff(closes[-15:]).clip(min=0)) / 
                                 (abs(np.mean(np.diff(closes[-15:]).clip(max=0))) + 1e-8))
                volume_spike = volumes[-6:].sum() / (volumes[-20:-6].sum() + 1e-8)

                # Пик + перекупленность + взрывной объём
                if (price >= 0.00025 and
                    price == max(closes[-12:]) and           # текущая цена — максимум за час
                    rsi >= 82 and
                    change_15m >= 18 and
                    volume_spike >= 6):                       # объём ×6+ от среднего

                    coin = symbol.split('/')[0].replace('1000', '')

                    # === АВТОМАТИЧЕСКИЕ УРОВНИ ===
                    entry = price
                    stop_loss = price * 1.06                      # +6% (защита от выноса)
                    tp1 = price * 0.82                            # -18% (первый тейк)
                    tp2 = price * 0.65                            # -35% (второй тейк)
                    tp3 = price * 0.45                            # -55% (полный слив)

                    caption = f"""#ШОРТ {coin} НА ПИКЕ
Вход: <code>{entry:.6f}</code>
Stop-Loss: <code>{stop_loss:.6f}</code> (+6%)
TP1: <code>{tp1:.6f}</code> (-18%)
TP2: <code>{tp2:.6f}</code> (-35%)
TP3: <code>{tp3:.6f}</code> (-55%)
RSI {rsi:.1f}% | Объём ×{volume_spike:.1f}
MEXC → https://mexc.com/exchange/{symbol.replace('/', '_')}"""

                    chart = draw_chart(ohlcv[-40:])
                    requests.post(
                        f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                        data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                        files={"photo": ("short.png", chart, "image/png")}
                    )
                    
                    sent.add(symbol)
                    print(f"ШОРТ-КИЛЛЕР → {coin} | вход {entry:.6f} | RSI {rsi:.1f}")
                    time.sleep(5)

            except: continue
                
        print(f"{datetime.now().strftime('%H:%M:%S')} — сканирую дампы")
        time.sleep(65)
        
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(30)
