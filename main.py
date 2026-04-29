from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN    = os.environ.get("BOT_TOKEN")
CHAT_ID  = os.environ.get("CHAT_ID")
SECRET   = os.environ.get("SECRET", "")
DEPOSIT  = float(os.environ.get("DEPOSIT", "10000"))

RISK_PCT = 1.0

# Pip value по парах
PIP_VALUES = {
    "EURUSD": 10.0,
    "GBPUSD": 10.0,
    "AUDUSD": 10.0,
    "USDJPY": 9.1,
    "XAUUSD": 1.0,   # Gold: $1 per 0.01 lot per point
}

PIP_SIZES = {
    "EURUSD": 10000,
    "GBPUSD": 10000,
    "AUDUSD": 10000,
    "USDJPY": 100,
    "XAUUSD": 100,
}

def calc_lot(pair: str, entry: float, sl: float) -> float:
    pip_size  = PIP_SIZES.get(pair, 10000)
    pip_value = PIP_VALUES.get(pair, 10.0)
    sl_pips   = abs(entry - sl) * pip_size
    if sl_pips == 0:
        return 0.01
    risk_usd = DEPOSIT * RISK_PCT / 100
    lot = risk_usd / (sl_pips * pip_value)
    return max(0.01, round(lot, 2))

def send_telegram(msg: str):
    if not TOKEN or not CHAT_ID:
        print("[WARN] BOT_TOKEN або CHAT_ID не задані")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }, timeout=10)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    try:
        d = data if isinstance(data, dict) else {}

        if SECRET and d.get('secret') != SECRET:
            return {"status": "unauthorized"}, 401

        msg_type = d.get('type', 'SIGNAL')

        # ── Лондонська сесія ──────────────────────────────────
        if msg_type == 'SESSION':
            send_telegram(
                "🌍 <b>ЛОНДОНСЬКА СЕСІЯ ВІДКРИТА</b>\n"
                "────────────────────────\n"
                "🕗 08:00 UTC — ринок активний\n"
                "Очікуємо SMC сигнали на:\n"
                "• EURUSD • GBPUSD\n"
                "• AUDUSD • USDJPY • XAUUSD"
            )
            return {"status": "ok", "type": "session"}, 200

        # ── Торговий сигнал ───────────────────────────────────
        pair   = d.get('pair',  'EURUSD')
        dr     = d.get('dir',   '?')
        entry  = float(d.get('entry', 0))
        sl     = float(d.get('sl',    0))
        tp1    = float(d.get('tp1',   0))
        tp2    = float(d.get('tp2',   0))
        score  = d.get('score', '?')
        tf     = d.get('tf',    'M15')
        tm     = d.get('time',  '')

        lot      = calc_lot(pair, entry, sl)
        risk_usd = round(DEPOSIT * RISK_PCT / 100, 2)
        r        = abs(entry - sl)
        rr       = round(abs(tp2 - entry) / r, 1) if r > 0 else 0

        direction_icon = '🟢 LONG' if dr == 'LONG' else '🔴 SHORT'

        # Іконка пари
        pair_icons = {
            "EURUSD": "🇪🇺",
            "GBPUSD": "🇬🇧",
            "AUDUSD": "🇦🇺",
            "USDJPY": "🇯🇵",
            "XAUUSD": "🥇",
        }
        pair_icon = pair_icons.get(pair, "💱")

        msg = (
            f"⚡ <b>SMC СИГНАЛ</b>\n"
            f"{'─' * 24}\n"
            f"{direction_icon}  |  {pair_icon} <b>{pair}</b>  |  {tf}\n"
            f"{'─' * 24}\n"
            f"📍 <b>Entry</b>  : <code>{entry:.5f}</code>\n"
            f"🛑 <b>SL</b>     : <code>{sl:.5f}</code>\n"
            f"🎯 <b>TP1</b>    : <code>{tp1:.5f}</code>\n"
            f"🏆 <b>TP2</b>    : <code>{tp2:.5f}</code>\n"
            f"{'─' * 24}\n"
            f"📦 <b>Лот</b>    : <code>{lot:.2f}</code>\n"
            f"💰 <b>Ризик</b>  : <code>{risk_usd:.2f} USD ({RISK_PCT}%)</code>\n"
            f"🏦 <b>Депозит</b>: <code>{DEPOSIT:.0f} USD</code>\n"
            f"📊 <b>RR</b>     : <code>1:{rr}</code>\n"
            f"⭐ <b>Score</b>  : <code>{score}</code>\n"
            f"{'─' * 24}\n"
            f"🕐 {tm}"
        )

        send_telegram(msg)
        return {"status": "ok", "lot": lot}, 200

    except Exception as e:
        send_telegram(f"❌ Webhook помилка: {e}")
        return {"status": "error", "msg": str(e)}, 500

@app.route('/', methods=['GET'])
def index():
    return {"status": "running", "deposit": DEPOSIT}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
