# app.py
import os, json, datetime
from decimal import Decimal, ROUND_DOWN
from flask import Flask, request, jsonify
from broker_stub import place_market_buy, place_market_sell  # stub - replace for real broker

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_secret_12345")
PORT = int(os.getenv("PORT", 5000))

CONFIG_FILE = "config.json"
BALANCES_FILE = "balances.json"
POSITIONS_FILE = "positions.json"   # currently open positions

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# Ensure files exist
config = load_json(CONFIG_FILE, {"starting_capital": 150})
balances = load_json(BALANCES_FILE, {})
positions = load_json(POSITIONS_FILE, {})

# initialize balances for any new symbols in config (optionally)
for s, amt in balances.items():
    # ensure decimal-like numbers
    balances[s] = float(amt)

app = Flask(__name__)

def log(msg):
    line = f"{datetime.datetime.utcnow().isoformat()} - {msg}"
    print(line)
    with open("events.log", "a") as f:
        f.write(line + "\n")

def quant(x):
    # round money to 2 decimals
    return float(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_DOWN))

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data or data.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    ticker = (data.get("ticker") or data.get("symbol") or "").upper()
    signal = (data.get("signal") or "").lower()
    price = data.get("price")
    if not ticker or not signal or price is None:
        return jsonify({"error":"missing fields (need ticker, signal, price)"}), 400
    try:
        price = float(price)
    except:
        return jsonify({"error":"invalid price"}), 400

    # ensure symbol exists in balances (auto-add if not)
    if ticker not in balances:
        balances[ticker] = float(config.get("starting_capital", 150))
        save_json(BALANCES_FILE, balances)

    if signal == "buy":
        return handle_buy(ticker, price)
    elif signal == "sell":
        return handle_sell(ticker, price)
    else:
        return jsonify({"status":"ignored","reason":"unknown signal"}), 200

def handle_buy(ticker, price):
    bal = Decimal(str(balances.get(ticker, config.get("starting_capital",150))))
    if bal <= 0:
        return jsonify({"status":"no-funds"}), 200

    allocation = bal  # 100% compounding
    # compute quantity to buy
    qty = float((allocation / Decimal(str(price))))
    if qty <= 0:
        return jsonify({"status":"too-small-allocation"}), 200

    # Place order via broker (stub). Replace function to integrate your broker.
    resp = place_market_buy(ticker, qty)
    if resp.get("status") != "filled":
        log(f"BUY FAILED for {ticker}: {resp}")
        return jsonify({"status":"order_failed","detail":resp}), 500

    # Update position: store qty and avg_price
    positions[ticker] = {
        "qty": float(resp.get("filled_qty", qty)),
        "avg_price": float(resp.get("exec_price", price)),
        "last_buy_time": datetime.datetime.utcnow().isoformat()
    }
    # when buying, we spend allocation => set balance to 0 until closed
    balances[ticker] = 0.0
    save_json(BALANCES_FILE, balances)
    save_json(POSITIONS_FILE, positions)

    log(f"BUY filled {ticker} qty={positions[ticker]['qty']} @ {positions[ticker]['avg_price']}")
    return jsonify({"status":"filled","ticker":ticker,"qty":positions[ticker]["qty"]}), 200

def handle_sell(ticker, price):
    pos = positions.get(ticker)
    if not pos:
        return jsonify({"status":"no_position"}), 200

    qty = pos.get("qty")
    # Place sell via broker stub
    resp = place_market_sell(ticker, qty)
    if resp.get("status") != "filled":
        log(f"SELL FAILED for {ticker}: {resp}")
        return jsonify({"status":"order_failed","detail":resp}), 500

    exec_price = float(resp.get("exec_price", price))
    proceeds = float(Decimal(str(qty * exec_price)).quantize(Decimal("0.01")))
    # Full compounding: new balance = proceeds (you can include fees later)
    balances[ticker] = float(proceeds)
    # remove open position
    positions.pop(ticker, None)
    save_json(BALANCES_FILE, balances)
    save_json(POSITIONS_FILE, positions)

    log(f"SOLD {ticker} qty={qty} @ {exec_price} proceeds={proceeds}")
    return jsonify({"status":"sold","ticker":ticker,"proceeds":proceeds}), 200

# ADMIN endpoints to add/remove/update balances (protected by secret)
@app.route("/admin/list", methods=["GET"])
def admin_list():
    secret = request.args.get("secret")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error":"unauthorized"}), 401
    return jsonify({"balances": balances, "positions": positions})

@app.route("/admin/add", methods=["POST"])
def admin_add():
    data = request.json or {}
    if data.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error":"unauthorized"}), 401
    symbol = (data.get("symbol") or "").upper()
    amount = data.get("amount")
    if not symbol or amount is None:
        return jsonify({"error":"missing symbol or amount"}), 400
    balances[symbol] = float(amount)
    save_json(BALANCES_FILE, balances)
    return jsonify({"status":"ok","balances":balances})

@app.route("/admin/remove", methods=["POST"])
def admin_remove():
    data = request.json or {}
    if data.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error":"unauthorized"}), 401
    symbol = (data.get("symbol") or "").upper()
    if not symbol:
        return jsonify({"error":"missing symbol"}), 400
    balances.pop(symbol, None)
    positions.pop(symbol, None)
    save_json(BALANCES_FILE, balances)
    save_json(POSITIONS_FILE, positions)
    return jsonify({"status":"ok","balances":balances})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)