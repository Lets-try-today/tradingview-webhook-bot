# broker_ibkr.py
from ib_insync import *
import time

# Connect automatically when this file is imported
def connect_ibkr():
    try:
        ib = IB()
        ib.connect("127.0.0.1", 7494, clientId=1)  # PAPER TWS
        print("Connected to IBKR TWS")
        return ib
    except Exception as e:
        print("Connection error:", e)
        return None

ib = connect_ibkr()


def place_market_buy(symbol, amount_usd):
    """
    Buys using USD not quantity.
    Converts USD → qty based on market price.
    """
    if ib is None:
        return {"status": "error", "message": "Not connected to IBKR"}

    contract = Stock(symbol, "SMART", "USD")
    ib.qualifyContracts(contract)

    # Get current market price
    market = ib.reqMktData(contract, "", False, False)
    time.sleep(1)
    price = float(market.last or market.close)
    if price <= 0:
        return {"status": "error", "message": "Invalid price"}

    qty = round(amount_usd / price, 2)

    order = MarketOrder("BUY", qty)
    trade = ib.placeOrder(contract, order)

    trade.waitUntilDone()

    return {
        "status": "filled",
        "symbol": symbol,
        "qty": qty,
        "exec_price": trade.orderStatus.avgFillPrice,
        "filled_value": qty * trade.orderStatus.avgFillPrice
    }


def place_market_sell(symbol, qty):
    if ib is None:
        return {"status": "error", "message": "Not connected"}

    contract = Stock(symbol, "SMART", "USD")
    ib.qualifyContracts(contract)

    order = MarketOrder("SELL", qty)
    trade = ib.placeOrder(contract, order)

    trade.waitUntilDone()

    return {
        "status": "filled",
        "symbol": symbol,
        "qty": qty,
        "exec_price": trade.orderStatus.avgFillPrice
    }