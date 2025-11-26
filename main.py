import ccxt
import time
import requests
import os
from datetime import datetime

# Берём токен и чат из переменных окружения Render (безопасно!)
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
        )
    except:
        pass

ex = ccxt.mexc()
sent = set()

print("Сканер пампов запущен на Render! Жду жирные движения...")

while True:
    try:
        markets = ex.load_markets()
        symbols = [s for s in markets if s.endswith('/USDT') and markets[s]['spot']]
        
        for symbol in symbols:
            if symbol in sent:
                continue
            try:
                ohlcv = ex.fetch_ohlcv(symbol, '5m', limit=20)
                if len(ohlcv) < 15:
                    continue
                    
                closes = [x[4] for x in ohlcv]
                change = (closes[-1] - closes[-10]) / closes[-10] * 100
                volume_usd = sum(x[5] * x[4] for x in ohlcv[-12:])
                price = closes[-1]
                
                if change >= 7.5 and volume_usd >= 500000 and price >= 0.0003:
                    coin = symbol.split('/')[0].replace('1000', '')
                    msg = f"""#{coin} PUMP +{change:.1f}%
💰 Цена: ${price:.6f}
🔥 Объём: ${(volume_usd/1000000):.2f}M
MEXC → https://mexc.com/exchange/{symbol.replace('/', '_')}"""
                    
                    send(msg)
                    sent.add(symbol)
                    print(f"Сигнал отправлен → {coin} +{change:.1f}%")
                    time.sleep(2)
            except:
                continue
                
        print(f"{datetime.now().strftime('%H:%M:%S')} — цикл завершён, сплю 90 сек")
        time.sleep(90)
        
    except Exception as e:
        print("Ошибка в главном цикле:", e)
        time.sleep(30)
