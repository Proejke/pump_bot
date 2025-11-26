import ccxt, time, requests, os
from datetime import datetime

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ex = ccxt.mexc()
sent = set()

print("Сканер запущен — жду пампы от 6.5%")

while True:
    try:
        for symbol in [s for s in ex.load_markets() if s.endswith('/USDT') and ex.markets[s]['spot']]:
            if symbol in sent: continue
            try:
                o = ex.fetch_ohlcv(symbol, '5m', limit=25)
                if len(o) < 20: continue
                closes = [x[4] for x in o]
                change = (closes[-1] - closes[-10]) / closes[-10] * 100
                volume = sum(x[5] * x[4] for x in o[-15:])
                price = closes[-1]

                if change >= 6.5 and volume >= 300000 and price >= 0.0001:
                    coin = symbol.split('/')[0].replace('1000','')
                    msg = f"""#{coin} FAST PUMP
+{change:.2f}%
Цена: ${price:.6f}
Объём 15 свечей: ${(volume/1e6):.2f}M
MEXC → https://mexc.com/exchange/{symbol.replace('/', '_')}"""

                    try:
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                    data={"chat_id": CHAT_ID, "text": msg, "disable_web_page_preview": True})
                        sent.add(symbol)
                        print(f"Сигнал отправлен → {coin} +{change:.1f}%")
                    except: pass
                    time.sleep(2)
            except: continue

        print(f"{datetime.now().strftime('%H:%M:%S')} — цикл ок")
        time.sleep(80)

    except Exception as e:
        print("Ошибка:", e)
        time.sleep(30)
