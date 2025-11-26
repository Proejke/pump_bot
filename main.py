import ccxt, time, requests, os, io
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# === ТОКЕН И ЧАТ ===
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

mexc = ccxt.mexc()
bybit = ccxt.bybit({'options': {'defaultType': 'swap'}})
sent = set()

# === Проверка фьючерсов ===
def has_futures_anywhere(base):
    try:
        markets = mexc.load_markets()
        if any(base + 'USDT' in s for s in markets if markets[s].get('swap') or 'PERP' in s):
            return 'mexc'
    except: pass
    try:
        if base + '/USDT:USDT' in bybit.load_markets():
            return 'bybit'
    except: pass
    return False

# === Рисуем график с уровнями ===
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

    highs = []
    lows = []
    window = 8
    for i in range(window, len(closes) - window):
        if closes[i] == max(closes[i-window:i+window+1]):
            highs.append(closes[i])
        if closes[i] == min(closes[i-window:i+window+1]):
            lows.append(closes[i])

    resistance = max(highs[-12:]) if highs else price * 1.025
    supports = sorted(set([p for p in lows[-18:] if p < price * 0.97]), reverse=True)[:3]

    # Сопротив
