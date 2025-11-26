import ccxt, time, requests, os
from datetime import datetime

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ex = ccxt.mexc()
sent = set()

print("Сканер v2 — ловит пампы за 15–25 мин до пика")

while True:
    try:
        markets = ex.load_markets()
        for symbol in [s for s in markets if s.endswith('/USDT') and markets[s]['spot']]:
            if symbol in sent: continue
            try:
                o = ex.fetch_ohlcv(symbol, '5m', limit=30)
                if len(o) < 25: continue
                
                closes = [x[x[4] for x in o]
                # рост за последние 4–8 свечей (20–40 минут)
                change_4 = (closes[-1] - closes[-5]) / closes[-5] * 100   # ~20 мин
                change_8 = (closes[-1] - closes[-9]) / closes[-9] * 100   # ~40 мин
                
                volume_last = sum(x[5] * x[4] for x in o[-8:])  # объём за 40 мин
                price = closes[-1]

                # Ловим именно начало взрыва
                if (change_4 >= 7.0 or change_8 >= 11.0) and volume_last >= 500000 and price >= 0.0001:
                    coin = symbol.split('/')[0].replace('1000','')
                    msg = f"""IRYS FAST PUMP
+{max(change_4, change_8):.2f}% за последние 40 мин
Цена сейчас: ${price:.6f}
Объём: ${(volume_last/1e6):.2f}M
MEXC → https://mexc.com/exchange/{symbol.replace('/', '_')}"""

                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                data={"chat_id": CHAT_ID, "text": msg})
                    sent.add(symbol)
                    print(f"Сигнал → {coin} +{max(change_4, change_8):.1f}%")
                    time.sleep(2)
            except: continue

        print(f"{datetime.now().strftime('%H:%M:%S')} — проверка завершена")
        time.sleep(65)  # проверяем каждые ~65 сек

    except Exception as e:
        print("Ошибка:", e)
        time.sleep(20)
