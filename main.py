from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ── ENV змінні ────────────────────────────────────────────────────
TOKEN    = os.environ.get("BOT_TOKEN")   # Telegram bot token
CHAT_ID  = os.environ.get("CHAT_ID")    # Telegram chat id
SECRET   = os.environ.get("SECRET", "")  # Секрет для захисту webhook
DEPOSIT  = float(os.environ.get("DEPOSIT", "10000"))  # Депозит в USD (міняти в .env)

RISK_PCT  = 1.0   # % ризику на угоду
PIP_VALUE = 10.0  # $10 за 1 лот на EURUSD (стандарт)

# ── Розрахунок лотності ───────────────────────────────────────────
def calc_lot(entry: float, sl: float) -> float:
    """
    Лот = (Депозит * Ризик%) / (SL в піпсах * PipValue)
    """
    sl_pips = abs(entry - sl) * 10000  # конвертуємо в піпси
    if sl_pips == 0:
        return 0.01
    risk_usd = DEPOSIT * RISK_PCT / 100
    lot = risk_usd / (sl_pips * PIP_VALUE)
    lot = max(0.01, round(lot, 2))
    return lot

# ── Telegram відправка ────────────────────────────────────────────
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

# ── Webhook endpoint ──────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    try:
        d = data if isinstance(data, dict) else {}

        # Перевірка секрету
        if SECRET and d.get('secret') != SECRET:
            return {"status": "unauthorized"}, 401

        pair  = d.get('pair',  'EURUSD')
        dr    = d.get('dir',   '?')       # LONG або SHORT
        entry = float(d.get('entry', 0))
        sl    = float(d.get('sl',    0))
        tp    = float(d.get('tp',    0))
        tf    = d.get('tf',    'M15')
        tm    = d.get('time',  '')

        lot = calc_lot(entry, sl)

        direction_icon = '🟢 LONG' if dr == 'LONG' else '🔴 SHORT'

        msg = (
            f"⚡ <b>SMC СИГНАЛ</b>\n"
            f"{'─' * 22}\n"
            f"{direction_icon}  |  <b>{pair}</b>  |  {tf}\n"
            f"{'─' * 22}\n"
            f"📍 Entry   : <code>{entry:.5f}</code>\n"
            f"🛑 SL      : <code>{sl:.5f}</code>\n"
            f"🎯 TP      : <code>{tp:.5f}</code>\n"
            f"📦 Lot     : <code>{lot:.2f}</code>\n"
            f"💰 Risk    : <code>{DEPOSIT * RISK_PCT / 100:.2f} USD  ({RISK_PCT}%)</code>\n"
            f"🏦 Deposit : <code>{DEPOSIT:.0f} USD</code>\n"
            f"{'─' * 22}\n"
            f"🕐 {tm}"
        )

        send_telegram(msg)
        return {"status": "ok", "lot": lot}, 200

    except Exception as e:
        send_telegram(f"❌ Webhook помилка: {e}")
        return {"status": "error", "msg": str(e)}, 500

# ── Health check ──────────────────────────────────────────────────
@app.route('/', methods=['GET'])
def index():
    return {"status": "running", "deposit": DEPOSIT}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
