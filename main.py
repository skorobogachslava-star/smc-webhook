from flask import Flask, request
import requests
import os

app    = Flask(__name__)
TOKEN  = os.environ.get("BOT_TOKEN")
CHATID = os.environ.get("CHAT_ID")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    try:
        d    = data if isinstance(data, dict) else {}
        pair = d.get('pair', 'EURUSD')
        dr   = d.get('dir',  '?')
        ent  = d.get('entry','?')
        sc   = d.get('score','?')
        tf   = d.get('tf',   'H1')
        tm   = d.get('time', '')
        msg  = (f"🔔 SMC СИГНАЛ\n"
                f"{'🟢 LONG' if dr=='LONG' else '🔴 SHORT'} {pair}\n"
                f"📍 Entry : {ent}\n"
                f"⭐ Score : {sc}/7\n"
                f"⏱ TF    : {tf}\n"
                f"🕐 Час   : {tm}")
    except:
        msg = str(data)
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHATID, "text": msg}
    )
    return "OK", 200

@app.route('/', methods=['GET'])
def home():
    return "SMC Webhook running!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
