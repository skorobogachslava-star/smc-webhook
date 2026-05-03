from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN    = os.environ.get("BOT_TOKEN")
CHAT_ID  = os.environ.get("CHAT_ID")
SECRET   = os.environ.get("SECRET", "")
DEPOSIT  = float(os.environ.get("DEPOSIT", "25000"))
RISK_PCT = 1.0

# XAU: 1 лот = 100 oz, pip = $0.01 → pip_value = 1.0, pip_size = 100
PIP_VALUES = {"XAUUSD": 1.0}
PIP_SIZES  = {"XAUUSD": 100}

def calc_lot(entry: float, sl: float) -> float:
    sl_pips  = abs(entry - sl) * PIP_SIZES["XAUUSD"]
    if sl_pips == 0:
        return 0.01
    risk_usd = DEPOSIT * RISK_PCT / 100
    lot = risk_usd / (sl_pips * PIP_VALUES["XAUUSD"])
    return max(0.01, round(lot, 2))

def send_telegram(msg: str):
    if not TOKEN or not CHAT_ID:
        print("[WARN] BOT_TOKEN або CHAT_ID не задані")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id":    CHAT_ID,
        "text":       msg,
        "parse_mode": "HTML"
    }, timeout=10)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    try:
        d = data if isinstance(data, dict) else {}

        # Перевірка секрету
        if SECRET and d.get('secret') != SECRET:
            return {"status": "unauthorized"}, 401

        event  = d.get('event',    'ENTRY')
        pair   = d.get('pair',     'XAUUSD')
        dr     = d.get('dir',      '?')
        price  = float(d.get('price',  d.get('entry', 0)))
        sl     = float(d.get('sl',     0))
        tp1    = float(d.get('tp1',    0))
        tp2    = float(d.get('tp2',    0))
        tp3    = float(d.get('tp3',    0))
        lots   = d.get('lots',     None)
        tm     = d.get('time',     '')

        risk_usd = round(DEPOSIT * RISK_PCT / 100, 2)
        lot      = float(lots) if lots else calc_lot(price, sl)
        r        = abs(price - sl)
        rr1      = round(abs(tp1 - price) / r, 1) if r > 0 else 0
        rr3      = round(abs(tp3 - price) / r, 1) if r > 0 else 0

        dir_icon = '🟢 LONG' if dr == 'LONG' else '🔴 SHORT'
        SEP = '─' * 26

        # ── ENTRY ──────────────────────────────────────────
        if event == 'ENTRY':
            msg = (
                f"⚡ <b>WAVE62 СИГНАЛ</b>\n"
                f"{SEP}\n"
                f"{dir_icon}  |  🥇 <b>{pair}</b>  |  M5\n"
                f"{SEP}\n"
                f"📍 <b>Entry</b>  : <code>{price:.2f}</code>\n"
                f"🛑 <b>SL</b>     : <code>{sl:.2f}</code>\n"
                f"🎯 <b>TP1</b>    : <code>{tp1:.2f}</code>  <i>(40% @ 1R)</i>\n"
                f"🟠 <b>TP2</b>    : <code>{tp2:.2f}</code>  <i>(30% @ 3R)</i>\n"
                f"🏆 <b>TP3</b>    : <code>{tp3:.2f}</code>  <i>(30% @ 8R)</i>\n"
                f"{SEP}\n"
                f"📦 <b>Лот</b>    : <code>{lot:.2f}</code>\n"
                f"💰 <b>Ризик</b>  : <code>{risk_usd:.2f} USD ({RISK_PCT}%)</code>\n"
                f"🏦 <b>Депозит</b>: <code>{DEPOSIT:.0f} USD</code>\n"
                f"📐 <b>RR max</b> : <code>1:{rr3}</code>\n"
                f"{SEP}\n"
                f"🕐 {tm}"
            )

        # ── TP1 ────────────────────────────────────────────
        elif event == 'TP1_HIT':
            msg = (
                f"✅ <b>TP1 ДОСЯГНУТО</b>  |  {dir_icon}\n"
                f"{SEP}\n"
                f"🥇 <b>{pair}</b>\n"
                f"🎯 TP1 @ <code>{tp1:.2f}</code>  <i>(40% закрито)</i>\n"
                f"🔄 SL перенесено на <b>беззбиток</b>\n"
                f"🟠 Далі TP2 @ <code>{tp2:.2f}</code>\n"
                f"{SEP}\n"
                f"🕐 {tm}"
            )

        # ── TP2 ────────────────────────────────────────────
        elif event == 'TP2_HIT':
            msg = (
                f"💰 <b>TP2 ДОСЯГНУТО</b>  |  {dir_icon}\n"
                f"{SEP}\n"
                f"🥇 <b>{pair}</b>\n"
                f"🟠 TP2 @ <code>{tp2:.2f}</code>  <i>(30% закрито)</i>\n"
                f"🏆 Далі TP3 @ <code>{tp3:.2f}</code>  <i>(фінал 30%)</i>\n"
                f"{SEP}\n"
                f"🕐 {tm}"
            )

        # ── TP3 ────────────────────────────────────────────
        elif event == 'TP3_HIT':
            msg = (
                f"🏆 <b>TP3 — УГОДА ЗАКРИТА ПОВНІСТЮ</b>\n"
                f"{SEP}\n"
                f"🥇 <b>{pair}</b>  |  {dir_icon}\n"
                f"✅ TP3 @ <code>{tp3:.2f}</code>  <i>(+8R!)</i>\n"
                f"💰 Прибуток: ~<code>{round(risk_usd * rr3, 2)} USD</code>\n"
                f"{SEP}\n"
                f"🕐 {tm}"
            )

        # ── SL ─────────────────────────────────────────────
        elif event == 'SL_HIT':
            msg = (
                f"❌ <b>СТОП-ЛОСС</b>  |  {dir_icon}\n"
                f"{SEP}\n"
                f"🥇 <b>{pair}</b>\n"
                f"🛑 SL @ <code>{sl:.2f}</code>\n"
                f"💸 Збиток: ~<code>{risk_usd} USD ({RISK_PCT}%)</code>\n"
                f"{SEP}\n"
                f"🕐 {tm}"
            )

        # ── MAX HOLD ───────────────────────────────────────
        elif event == 'MAX_HOLD':
            pnl_dir = '📈' if (dr == 'LONG' and price > float(d.get('entry', price))) else '📉'
            msg = (
                f"⏰ <b>24г ТАЙМ-АУТ</b>  |  {dir_icon}\n"
                f"{SEP}\n"
                f"🥇 <b>{pair}</b>\n"
                f"📍 Закрито @ <code>{price:.2f}</code>\n"
                f"{SEP}\n"
                f"🕐 {tm}"
            )

        # ── П'ЯТНИЦЯ ───────────────────────────────────────
        elif event == 'FRI_CLOSE':
            msg = (
                f"📅 <b>П'ЯТНИЦЯ — ПРИМУСОВЕ ЗАКРИТТЯ</b>\n"
                f"{SEP}\n"
                f"🥇 <b>{pair}</b>  |  {dir_icon}\n"
                f"📍 Закрито @ <code>{price:.2f}</code>\n"
                f"{SEP}\n"
                f"🕐 {tm}"
            )

        # ── НЕВІДОМА ПОДІЯ ─────────────────────────────────
        else:
            msg = (
                f"ℹ️ <b>{event}</b>  |  {dir_icon}\n"
                f"🥇 <b>{pair}</b> @ <code>{price:.2f}</code>\n"
                f"🕐 {tm}"
            )

        send_telegram(msg)
        return {"status": "ok", "event": event, "lot": lot}, 200

    except Exception as e:
        send_telegram(f"❌ Webhook помилка: {e}")
        return {"status": "error", "msg": str(e)}, 500

@app.route('/', methods=['GET'])
def index():
    return {"status": "running", "deposit": DEPOSIT, "pair": "XAUUSD"}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
