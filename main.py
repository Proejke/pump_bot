import ccxt, time, requests, os, io
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

mexc = ccxt.mexc()
bybit = ccxt.bybit({'options': {'defaultType': 'swap'}})
sent = set()

def has_futures_anywhere(base):
    try:
        markets = mexc.load_markets()
        if any('USDT' in s and markets[s].get('swap') for s in markets if base in s):
            return 'mexc'
    except: pass
    try:
        if base + '/USDT:USDT' in bybit.load_markets():
            return 'bybit'
    except: pass
    return False

def draw_chart_with_levels(ohlcv):
    img = Image.new('RGB', (1200, 720), (18, 18, 28))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
        font_s = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
        font_s = font

    closes = [c[4] for c in ohlcv]
    high, low = max(closes), min(closes)
    width = 1200 // len(ohlcv)

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

    highs = []
    lows = []
    window = 8
    for i in range(window, len(closes) - window):
        if closes[i] == max(closes[i-window:i+window+1]):
            highs.append(closes[i])
        if closes[i] == min(closes[i-window:i+window+1]):
            lows.append(closes[i])

    resistance = max(highs[-12:] or [price * 1.025])
    supports = sorted({p for p in lows[-18:] if p < price * 0.97}, reverse=True)[:3]

    y_r = int(650 - (resistance - low)/(high-low+1e-9)*600)
    draw.line([(40, y_r), (1160, y_r)], fill=(255,70,70), width=5)
    draw.text((50, y_r-35), f"Сопротивление: {resistance:.6f}", fill=(255,100,100), font=font)

    for i, level in enumerate(supports):
        y = int(650 - (level - low)/(high-low+1e-9)*600)
        draw.line([(40, y), (1160, y)], fill=(0,255,140), width=3)
        draw.text((50, y-30), f"TP{i+1}: {level:.6f}", fill=(0,255,140), font=font)

    y_now = int(650 - (price - low)/(high-low+1e-9)*600)
    draw.line([(40, y_now), (1160, y_now)], fill=(100,180,255), width=4)
    draw.text((50, y_now-35), f"Сейчас: {price:.6f}", fill=(100,200,255), font=font)

    sl = round(price * 1.07, 8)
    y_sl = int(650 - (sl - low)/(high-low+1e-9)*600)
    for x in range(40, 1161, 15):
        draw.line([(x, y_sl-5), (x+8, y_sl-5)], fill=(255,255,255), width=2)
    draw.text((50, y_sl-35), f"SL +7%: {sl:.6f}", fill=(255,255,255), font=font_s)

    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return buf, resistance, supports, sl

print("ШОРТ-КИЛЛЕР 2025 | спайк ×3.3 — ЗАПУЩЕН")

while True:
    try:
        for symbol in [s for s in mexc.load_markets() if s.endswith('/USDT') and mexc.markets[s]['spot']]:
            base = symbol.split('/')[0].replace('1000','')
            if symbol in sent: continue

            platform = has_futures_anywhere(base)
            if not platform: continue

            ohlcv = mexc.fetch_ohlcv(symbol, '5m', limit=60)
            if len(ohlcv) < 50: continue

            closes = np.array([c[4] for c in ohlcv])
            price = closes[-1]
            change_20m = (price / closes[-5] - 1) * 100 if len(closes) > 5 else 0
            change_45m = (price / closes[-10] - 1) * 100 if len(closes) > 10 else 0

            delta = np.diff(closes[-15:])
            gain = np.mean(delta.clip(min=0))
            loss = abs(np.mean(delta.clip(max=0)))
            rsi = 100 - 100/(1 + gain/(loss + 1e-8)) if loss != 0 else 100

            volume_spike = sum(x[5] for x in ohlcv[-8:]) / max(1, sum(x[5] for x in ohlcv[-25:-8]))

            if (price >= 0.00015 and
                rsi >= 78 and
