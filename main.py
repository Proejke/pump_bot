import ccxt, time, requests, os, io, numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

TOKEN = "7815274707:AAHrvQbGbnWVM1c3U7FNuvs9q6VqVh5uGHU"
CHAT_ID = "5189732524"

mexc = ccxt.mexc()
bybit = ccxt.bybit({'options':{'defaultType':'swap'}})
sent = set()
print("ШОРТ-КИЛЛЕР AGGRESSIVE 2025 — РАБОТАЕТ 24/7")

while True:
    try:
        if time.time() % 21600 < 30: sent.clear()
        markets = mexc.load_markets()
        for s in [x for x in markets if x.endswith('/USDT') and markets[x]['spot']]:
            base = s.split('/')[0].replace('1000','')
            if s in sent: continue
            if not any('USDT' in x and markets[x].get('swap') for x in markets if base in x):
                try: 
                    if base+'/USDT:USDT' not in bybit.load_markets(): continue
                except: continue

            kl = mexc.fetch_ohlcv(s,'5m',limit=60)
            if len(kl)<50: continue
            c = np.array([x[4] for x in kl])
            price = c[-1]
            if price < 0.0001: continue

            ch15 = (price/c[-4]-1)*100
            rsi = 100-100/(1+np.mean(np.diff(c[-15:]).clip(min=0))/max(1e-8,abs(np.mean(np.diff(c[-15:]).clip(max=0)))))
            vol = sum(x[5] for x in kl[-6:]) / max(1,sum(x[5] for x in kl[-25:-6]))

            if rsi>=74 and vol>=2.9 and price>=max(c[-12:])*0.97 and ch15>=7:
                img=Image.new('RGB',(1200,720),(18,18,28))
                d=ImageDraw.Draw(img)
                try: f=ImageFont.truetype("arial.ttf",28)
                except: f=ImageFont.load_default()
                sl=round(price*1.07,8); tp1=round(price*0.88,8); tp2=round(price*0.75,8); tp3=round(price*0.60,8)
                d.text((50,50),f"ШОРТ {base}",fill=(255,100,100),font=f)
                d.text((50,100),f"Вход: {price:.8f}",fill=(255,255,255),font=f)
                d.text((50,150),f"SL +7%: {sl}",fill=(255,255,255),font=f)
                d.text((50,200),f"TP1 {tp1} │ TP2 {tp2} │ TP3 {tp3}",fill=(0,255,140),font=f)
                d.text((50,300),f"RSI {rsi:.1f} ×{vol:.1f}",fill=(100,200,255),font=f)
                b=io.BytesIO(); img.save(b,'PNG'); b.seek(0)

                cap = f"#ШОРТ {base}\nВход: <code>{price:.8f}</code>\nSL: <code>{sl}</code>\nTP1: <code>{tp1}</code>  TP2: <code>{tp2}</code>  TP3: <code>{tp3}</code>\nRSI {rsi:.1f}% ×{vol:.1f}"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                             data={"chat_id":CHAT_ID,"caption":cap,"parse_mode":"HTML"},
                             files={"photo":("short.png",b)})
                sent.add(s)
                print(f"СИГНАЛ → {base} {price:.6f}")
        print(f"{datetime.now():%H:%M:%S} сканирую агрессивно")
        time.sleep(35)
    except Exception as e: print("Ошибка:",e); time.sleep(15)
