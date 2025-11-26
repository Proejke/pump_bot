import ccxt, time, requests, os, io
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# === ТОКЕН И ЧАТ ===
TOKEN = os.getenv("TOKEN")      # твой бот-токен
CHAT_ID = os.getenv("CHAT_ID")  # твой чат-id

mexc = ccxt.mexc()
bybit = ccxt.bybit({'options': {'defaultType': 'swap'}})
sent = set()  # защита от повторов

# === Проверка наличия фьючерсов (MEXC или ByBit) ===
def has_futures_anywhere(base):
    try:
        if any(base + 'USDT' in s for s in mexc.load_markets().keys() if 'PERP' in s):
            return 'mexc'
        if base + '/USDT:USDT' in bybit.load_markets():
            return 'bybit'
    except:
        pass
    return False

# === Отрисовка графика с уровнями ===
def draw_chart_with_levels(ohlcv):
    img = Image.new('RGB', (1200, 720), (18, 18, 28))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
        font_small = font

    closes = [c[4] for c in ohlcv]
    high, low = max(closes), min(closes)
    width = 1200 // len(ohlcv)

    # свечи
    for i, (t, o, h, l, c, v) in enumerate(ohlcv):
        x = i * width + 40
        hy = int(650 - (h - low)/(high-low+1e-9)*600)
        ly = int(650 - (l - low)/(high-low+1e-9)*600)
        oy = int(650 - (o - low)/(high-low+1e-9)*600)
        cy = int(650 - (c - low)/(high-low+1e-9)*600)
        color = (255,255,140) if c >= o else (255,70,70)
        draw.line([(x + width//2, hy), (x + width//2, ly)], fill=color, width=3)
        draw.rectangle([x+10, min(oy,cy), x+width-10, max(oy,cy)], fill=color)

    price = closes[-1]

    # поиск локальных максимумов и минимумов
    highs = []
    lows = []
    window = 8
    for i in range(window, len(closes) - window):
        if closes[i] == max(closes[i-window:i+window+1]):
            highs.append(closes[i])
        if closes[i] == min(closes[i-window:i+window+1]):
            lows.append(closes[i])

    resistance = max(highs[-10:]) if highs else price * 1.02
    supports = sorted(set([p for p in lows[-15:] if p < price * 0.98]), reverse=True)[:3]

    # Сопротивление (красная)
    y_res = int(650 - (resistance - low)/(high-low+1e-9)*600)
    draw.line([(40, y_res), (1160, y_res)], fill=(255,70,70), width=5)
    draw.text((50, y_res-35), f"Сопротивление: {resistance:.6f}", fill=(255,100,100), font=font)

    # Поддержки (зелёные)
    for i, level in enumerate(supports):
        y = int(650 - (level - low)/(high-low+1e-9)*600)
        draw.line([(40, y), (1160, y)], fill=(0,255,140), width=3)
        draw.text((50, y-30), f"TP{i+1}: {level:.6f}", fill=(0,255,140), font=font)

    # Текущая цена (синяя)
    y_now = int(650 - (price - low)/(high-low+1e-9)*600)
    draw.line([(40, y_now), (1160, y_now)], fill=(100,180,255), width=4)
    draw.text((50, y_now-35), f"Сейчас: {price:.6f}", fill=(100,200,255), font=font)

    # Стоп-лосс (белая пунктирная)
    sl = round(price * 1.07, 8)
    y_sl = int(650 - (sl - low)/(high-low+1e-9)*600)
    draw.line([(40, y_sl), (1160, y_sl)], fill=(255,255,255), width=3)
    for x in range(40, 1161, 15):
        draw.line([(x, y_sl-5), (x+8, y_sl-5)], fill=(255,255,255), width=2)
    draw.text((50, y_sl-35), f"SL: +7% → {sl:.6f}", fill=(255,255,255), font=font_small)

    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return buf, resistance, supports[:3], sl

print("ЗАПУЩЕН ШОРТ-КИЛЛЕР 2025 + УРОВНИ НА ГРАФИКЕ")

while True:
    try:
        for symbol in [s for s in mexc.load_markets() if s.endswith('/USDT') and mexc.markets[s]['spot']]:
            base = symbol.split('/')[0].replace('1000','')
            if symbol in sent: continue

            platform = has_futures_anywhere(base)
            if not platform: continue

            try:
                ohlcv = mexc.fetch_ohlcv(symbol, '5m', limit=60)
                if len(ohlcv) < 50: continue

                closes = np.array([x[4] for x in ohlcv])
                price = closes[-1]
                change_20m = (price / closes[-5] - 1) * 100
                change_45m = (price / closes[-10] - 1) * 100
                rsi = 100 - 100/(1 + np.mean(np.diff(closes[-15:]).clip(min=0)) / 
                                   (abs(np.mean(np.diff(closes[-15:]).clip(max=0)))+1e-8))
                volume_spike = sum(x[5] for x in ohlcv[-8:]) / max(1, sum(x[5] for x in ohlcv[-25:-8]))

                if (price >= 0.00015 and
                    rsi >= 78 and
                    price >= max(closes[-15:]) * 0.995 and
                    volume_spike >= 4 and
                    (change_20m >= 9 or change_45m >= 14)):

                    chart_buf, resistance, supports, sl = draw_chart_with_levels(ohlcv[-45:])

                    tp1 = supports[0] if len(supports)>0 else price*0.84
                    tp2 = supports[1] if len(supports)>1 else price*0.70
                    tp3 = supports[2] if len(supports)>2 else price*0.52

                    caption = f"""#ШОРТ {base} НА ПИКЕ 🔥
Вход: <code>{price:.8f}</code>
Stop-Loss: <code>{sl:.8f}</code> (+7%)
TP1: <code>{tp1:.8f}</code>
TP2: <code>{tp2:.8f}</code>
TP3: <code>{tp3:.8f}</code>
RSI {rsi:.1f}% │ Объём ×{volume_spike:.1f}
Фьючерсы: {platform.upper()}"""

                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                                data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                                files={"photo": ("short.png", chart_buf, "image/png")})

                    sent.add(symbol)
                    print(f"ШОРТ-СИГНАЛ → {base} | {price:.6f} | RSI {rsi:.1f}")
                    time.sleep(3)

            except Exception as e:
                continue

        print(f"{datetime.now().strftime('%H:%M:%S')} — сканирую пики для шорта")
        time.sleep(48)

    except Exception as e:
        print("Глобальная ошибка:", e)
        time.sleep(20)
