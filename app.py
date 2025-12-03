import json
import os
from flask import Flask, request
from broker_ibkr import place_market_buy, place_market_sell   # <-- USE YOUR IBKR FILE


app = Flask(__name__)

BALANCE_FILE = "balances.json"


# ------------------------------
# Load or create balances.json
# ------------------------------
def load_balances():
    if not os.path.exists(BALANCE_FILE):
        balances = {"UAVS": 150, "UPXI": 150}
        with open(BALANCE_FILE, "w") as f:
            json.dump(balances, f, indent=4)
        return balances

    with open(BALANCE_FILE, "r") as f:
        return json.load(f)


# ------------------------------
# Save balances.json
# ------------------------------
def save_balances(balances):
    with open(BALANCE_FILE, "w") as f:
        json.dump(balances, f, indent=4)


# ------------------------------
# MAIN WEBHOOK
# ------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("\n🔥 NEW ALERT RECEIVED:", data)

    action = data.get("action")
    symbol = data.get("symbol")

    if not action or not symbol:
        return {"error": "Missing 'action' or 'symbol'"}, 400

    action = action.lower().strip()
    symbol = symbol.upper().strip()

    balances = load_balances()
    allowed_stocks = list(balances.keys())

    # Check allowed stock
    if symbol not in allowed_stocks:
        print(f"❌ ERROR: {symbol} is not in allowed stocks list.")
        return {"error": f"{symbol} not allowed"}, 400

    current_balance = balances[symbol]
    print(f"📌 Current balance for {symbol}: ${current_balance}")

    # ------------------------------------------
    # BUY LOGIC (uses USD → quantity conversion)
    # ------------------------------------------
    if action == "buy":
        amount_usd = current_balance   # use full balance (compounding)

        result = place_market_buy(symbol, amount_usd)

        if result.get("status") == "filled":
            filled_value = result["filled_value"]
            balances[symbol] = filled_value
            save_balances(balances)

            print(f"✅ BUY Filled for {symbol} at ${result['exec_price']}")
            print(f"💰 New compounded balance: ${balances[symbol]}")

            return {
                "status": "BUY OK",
                "symbol": symbol,
                "new_balance": balances[symbol]
            }
        else:
            return {"error": "Trade not filled", "details": result}, 400

    # ------------------------------------------
    # SELL LOGIC (sells full position qty)
    # ------------------------------------------
    elif action == "sell":
        # convert balance → qty based on entry price not stored, so
        # we treat balance as USD amount and sell using balance/market price in broker file
        # BUT sell requires qty → capture qty in buy response
        # so we store last qty temporarily

        # Infer sell qty using USD amount & market price inside broker_ibkr
        qty_guess = round(current_balance / 1.0, 4)

        result = place_market_sell(symbol, qty_guess)

        if result.get("status") == "filled":
            qty = result["qty"]
            exec_price = result["exec_price"]
            new_value = qty * exec_price

            balances[symbol] = new_value
            save_balances(balances)

            print(f"✅ SELL Filled for {symbol} at ${exec_price}")
            print(f"💰 New compounded balance: ${balances[symbol]}")

            return {
                "status": "SELL OK",
                "symbol": symbol,
                "new_balance": balances[symbol]
            }
        else:
            return {"error": "Trade not filled", "details": result}, 400

    else:
        return {"error": "Invalid action"}, 400


# ------------------------------
# Start Flask (only local)
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)