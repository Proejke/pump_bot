import ccxt, time, requests, io, numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

TOKEN = "7815274707:AAHrvQbGbnWVM1c3U7FNuvs9q6VqVh5uGHU"
CHAT_ID = "5189732524"

mexc = ccxt.mexc({'rateLimit': 1000})  # пауза между запросами
bybit = ccxt.bybit({'options':{'defaultType':'swap'}, 'rateLimit': 1000})
sent = set()
last_reset = time.time()

print("ШОРТ-КИЛЛЕР AGGRESSIVE 2025 — ФИКСИРОВАННЫЙ")

while True:
    try:
        if time.time() - last_reset > 21600:  # сброс каждые 6 часов
            sent.clear()
            last_reset = time.time()

        # Загружаем рынки с паузой (чтобы не блочить)
        try:
            markets = mexc.load_markets()
        except Exception as e:
            print(f"MEXC блок: {e}. Жду 60 сек...")
            time.sleep(60)
            markets = {}  # заглушка, если совсем блочит

        # Только активные спот-пары с USDT (фильтр заранее, чтобы не грузить всё)
        symbols = [s for s in markets if s.endswith('/USDT') and markets[s].get('spot', False) and markets[s].get('active', True)]
        symbols = symbols[:200]  # первые 200, чтобы не превысить лимит

        for symbol in symbols:
            base = symbol.split('/')[0].replace('1000', '')
            if symbol in sent:
                continue

            # Проверка фьючерсов (с паузой)
            platform = None
            try:
                if any('USDT' in x and markets[x].get('swap') for x in markets if base in x):
                    platform = 'mexc'
                else:
                    bybit_markets = bybit.load_markets()
                    if base + '/USDT:USDT' in bybit_markets:
                        platform = 'bybit'
            except:
                pass

            if not platform:
                continue

            # Получаем OHLCV с паузой
            try:
                ohlcv = mexc.fetch_ohlcv(symbol, '5m', limit=60)
                if len(ohlcv) < 50:
                    continue
            except Exception as e:
                print(f"Ошибка OHLCV {symbol}: {e}")
                time.sleep(5)
                continue

            closes = np.array([x[4] for x in ohlcv])
            price = closes[-1]
            if price < 0.0001:
                continue

            change_15m = (price / closes[-4] - 1) * 100 if len(closes) > 4 else 0
            change_45m = (price / closes[-10] - 1) * 100 if len(closes) > 10 else 0

            delta = np.diff(closes[-15:])
            gain = np.mean(delta.clip(min=0))
            loss = abs(np.mean(delta.clip(max=0)))
            rsi = 100 - 100 / (1 + gain / (loss + 1e-8)) if loss != 0 else 100

            volume_spike = sum(x[5] for x in ohlcv[-6:]) / max(1, sum(x[5] for x in ohlcv[-25:-6]))

            if (rsi >= 74 and volume_spike >= 2.9 and price >= max(closes[-12:]) * 0.97 and (change_15m >= 7 or change_45m >= 12)):
                # Простой график (упрощённый, чтобы не жрать RAM)
                img = Image.new('RGB', (800, 400), (18,18,28))
                d = ImageDraw.Draw(img)
                try:
                    f = ImageFont.truetype("arial.ttf", 24)
                except:
                    f = ImageFont.load_default()
                sl = round(price * 1.07, 8)
                tp1 = round(price * 0.88, 8)
                tp2 = round(price * 0.75, 8)
                tp3 = round(price * 0.60, 8)
                d.text((10,10), f"ШОРТ {base}", fill=(255,100,100), font=f)
                d.text((10,40), f"Вход: {price:.8f}", fill=(255,255,255), font=f)
                d.text((10,70), f"SL +7%: {sl}", fill=(255,255,255), font=f)
                d.text((10,100), f"TP1 {tp1} | TP2 {tp2} | TP3 {tp3}", fill=(0,255,140), font=f)
                d.text((10,130), f"RSI {rsi:.1f} ×{volume_spike:.1f}", fill=(100,200,255), font=f)

                b = io.BytesIO()
                img.save(b, 'PNG')
                b.seek(0)

                cap = f"#ШОРТ {base}\nВход: <code>{price:.8f}</code>\nSL: <code>{sl}</code>\nTP1: <code>{tp1}</code> TP2: <code>{tp2}</code> TP3: <code>{tp3}</code>\nRSI {rsi:.1f}% ×{volume_spike:.1f}"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                             data={"chat_id":CHAT_ID,"caption":cap,"parse_mode":"HTML"},
                             files={"photo":("short.png",b)})
                sent.add(symbol)
                print(f"СИГНАЛ → {base} {price:.6f}")

            time.sleep(0.5)  # пауза между парами, чтобы не блочить

        print(f"{datetime.now().strftime('%H:%M:%S')} сканирую агрессивно")
        time.sleep(35)

    except Exception as e:
        print("Ошибка:", e)
        time.sleep(15)
