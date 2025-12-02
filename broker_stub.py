import time
import random

def place_market_buy(symbol, qty):
    time.sleep(0.2)
    exec_price = round(random.uniform(1.0, 1.2), 2)
    filled_value = qty * exec_price
    return {
        "status": "filled",
        "filled_qty": qty,
        "filled_value": filled_value,
        "exec_price": exec_price
    }

def place_market_sell(symbol, qty):
    time.sleep(0.2)
    exec_price = round(random.uniform(1.0, 1.3), 2)
    return {
        "status": "filled",
        "filled_qty": qty,
        "exec_price": exec_price
    }