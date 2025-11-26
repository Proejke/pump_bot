import ccxt
import time
import requests
from datetime import datetime

# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
TOKEN = os.getenv("TOKEN")         
CHAT_ID = os.getenv("CHAT_ID")
# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

def send(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
    try:
        requests.post(url, data=data)
    except:
        pass

exchange = ccxt.mexc()
sent = set()

print("Сканер пампов запущен на Render!")

while True:
    try:
        markets = exchange.load_markets()
        symbols = [s for s in markets if s.endswith('/USDT') and markets[s].get('spot')]
        
        for symbol in symbols:
            if symbol in sent:
                continue
                
            try:
                bars = exchange.fetch_ohlcv(symbol, '5m', limit=20)
                if len(bars) < 15:
                    continue
                    
                closes = [x[4] for x in bars]
                change = (closes[-1] - closes[-10]) / closes[-10] * 100
                volume_usd = sum(x[5] * x[4] for x in bars[-15:])
                price = closes[-1]
                
                if change >= 7.5 and volume_usd >= 500000 and price >= 0.0003:
                    coin = symbol.split('/')[0].replace('1000','')
                    msg = f"""{coin} FAST PUMP +{change:.1f}%
Цена: ${price:.6f}   Объём: ${(volume_usd/1e6):.2f}M
MEXC → https://mexc.com/exchange/{symbol.replace('/', '_')}"""
                    
                    send(msg)
                    sent.add(symbol)
                    print(f"Найден памп → {coin} +{change:.1f}%")
                    time.sleep(3)
            except:
                continue
                
        print(f"{datetime.now().strftime('%H:%M:%S')} — цикл завершён, спим 85 сек")
        time.sleep(85)
        
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(30)
