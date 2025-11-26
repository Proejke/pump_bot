import ccxt, time, requests, os
from datetime import datetime

TOKEN =           # ← замени
CHAT_ID =           # ← замени
def send(t):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                     data={"chat_id": CHAT_ID, "text": t})
    except: pass

ex = ccxt.mexc()
sent = set()

while True:
    try:
        syms = [s for s in ex.load_markets() if s.endswith('/USDT') and ex.markets[s]['spot']]
        for s in syms:
            if s in sent: continue
            try:
                o = ex.fetch_ohlcv(s, '5m', limit=20)
                if len(o)<15: continue
                c = [x[4] for x in o]
                ch = (c[-1]-c[-10])/c[-10]*100
                vol = sum(x[5]*x[4] for x in o[-12:])
                if ch>=7.5 and vol>=500000 and c[-1]>=0.0003:
                    coin = s.split('/')[0].replace('1000','')
                    msg = f"{coin} PUMP +{ch:.1f}%\n${c[-1]:.6f} | ${(vol/1e6):.1f}M vol\nhttps://mexc.com/exchange/{s.replace('/','_')}"
                    send(msg)
                    sent.add(s)
                    time.sleep(2)
            except: continue
        print(f"{datetime.now().strftime('%H:%M:%S')} ok")
        time.sleep(90)
    except Exception as e:
        print(e)
        time.sleep(30)
