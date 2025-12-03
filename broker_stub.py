import json
import random
import time

def place_market_buy(symbol, qty):
    """Simulated buy order - works on Render cloud."""
    time.sleep(0.1)
    return {
        "status": "filled",
        "filled_value": round(qty * 1.02, 2),  # Simulated 2% profit
        "exec_price": round(50 + random.random() * 20, 2)
    }

def place_market_sell(symbol, qty):
    """Simulated sell order - works on Render cloud."""
    time.sleep(0.1)
    return {
        "status": "filled",
        "exec_price": round(50 + random.random() * 20, 2)
    }
