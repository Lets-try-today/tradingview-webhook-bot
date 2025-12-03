import json
import os
from flask import Flask, request
from broker_ibkr import place_market_buy, place_market_sell   # IBKR broker functions

app = Flask(__name__)

BALANCE_FILE = "balances.json"


# ----------------------------------------------------
# Load or create balances.json
# ----------------------------------------------------
def load_balances():
    if not os.path.exists(BALANCE_FILE):
        # NEW STRUCTURE WITH qty & entry_price
        balances = {
            "UAVS": {"balance": 150, "qty": 0, "entry_price": 0},
            "UPXI": {"balance": 150, "qty": 0, "entry_price": 0}
        }
        with open(BALANCE_FILE, "w") as f:
            json.dump(balances, f, indent=4)
        return balances

    with open(BALANCE_FILE, "r") as f:
        return json.load(f)


# ----------------------------------------------------
# Save balances.json
# ----------------------------------------------------
def save_balances(balances):
    with open(BALANCE_FILE, "w") as f:
        json.dump(balances, f, indent=4)


# ----------------------------------------------------
# MAIN WEBHOOK ENDPOINT
# ----------------------------------------------------
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

    # Validate symbol
    if symbol not in balances:
        return {"error": f"{symbol} not allowed"}, 400

    current_balance = balances[symbol]["balance"]
    current_qty = balances[symbol]["qty"]
    current_entry = balances[symbol]["entry_price"]

    print(f"📌 Current balance = {current_balance}, qty = {current_qty}, entry = {current_entry}")


    # ----------------------------------------------------
    # BUY LOGIC (USD → Qty)
    # ----------------------------------------------------
    if action == "buy":
        amount_usd = current_balance  # compounding

        result = place_market_buy(symbol, amount_usd)

        if result.get("status") == "filled":
            # Store new quantity + entry price
            qty = result["qty"]
            price = result["exec_price"]
            filled_value = qty * price

            balances[symbol]["qty"] = qty
            balances[symbol]["entry_price"] = price
            balances[symbol]["balance"] = filled_value

            save_balances(balances)

            print(f"✅ BUY Filled for {symbol} → qty={qty}, price={price}")
            print(f"💰 New compounded balance = ${filled_value}")

            return {
                "status": "BUY OK",
                "symbol": symbol,
                "qty": qty,
                "entry_price": price,
                "new_balance": filled_value
            }

        return {"error": "Trade not filled", "details": result}, 400


    # ----------------------------------------------------
    # SELL LOGIC (Uses EXACT quantity)
    # ----------------------------------------------------
    elif action == "sell":

        if current_qty <= 0:
            return {"error": "No position to sell"}, 400

        qty_to_sell = current_qty  # exact qty

        result = place_market_sell(symbol, qty_to_sell)

        if result.get("status") == "filled":
            exec_price = result["exec_price"]
            final_value = qty_to_sell * exec_price

            # Update balance with sell value
            balances[symbol]["balance"] = final_value

            # RESET qty + entry_price after sell
            balances[symbol]["qty"] = 0
            balances[symbol]["entry_price"] = 0

            save_balances(balances)

            print(f"✅ SELL Filled for {symbol} @ {exec_price}")
            print(f"💰 New balance = ${final_value}")

            return {
                "status": "SELL OK",
                "symbol": symbol,
                "qty_sold": qty_to_sell,
                "exec_price": exec_price,
                "new_balance": final_value
            }

        return {"error": "Trade not filled", "details": result}, 400


    else:
        return {"error": "Invalid action"}, 400



# ----------------------------------------------------
# LOCAL FLASK RUN (not used on Render)
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)