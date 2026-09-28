"""
mock_data.py

Generates synthetic quotes in the exact shape data.fetch.get_live_data()
returns, so the rest of the pipeline (screening, SMMA, ETQ, ML) can be
built and demoed without hitting the real Fyers API -- useful outside
market hours or while iterating. Switch settings.MOCK_MODE = False and
this is bypassed entirely in favour of the real broker feed.
"""
import random

_state = {}


def get_mock_history(symbol, minutes=130):
    """Synthetic historical closes for mock mode, so SMMA seeding can
    be demonstrated end-to-end without a live broker connection."""
    base = random.uniform(80, 450)
    closes = []
    price = base
    for _ in range(minutes):
        price = max(1.0, price + random.uniform(-1.0, 1.0))
        closes.append(round(price, 2))
    _state[symbol] = {"ltp": closes[-1], "volume": random.randint(500_000, 2_000_000)}
    return closes


def get_mock_data(symbols):
    rows = []
    for symbol in symbols:
        if symbol not in _state:
            _state[symbol] = {
                "ltp": round(random.uniform(80, 450), 2),
                "volume": random.randint(500_000, 2_000_000),
            }
        s = _state[symbol]

        drift = random.uniform(-1.5, 1.5)
        if random.random() < 0.05:
            drift += random.choice([-1, 1]) * random.uniform(3, 8)
        s["ltp"] = max(1.0, round(s["ltp"] + drift, 2))
        s["volume"] += random.randint(1000, 50000)  # cumulative day volume only grows

        rows.append({
            "symbol": symbol,
            "ltp": s["ltp"],
            "volume": s["volume"],
            "bidQty": random.randint(200_000, 2_000_000),
            "askQty": random.randint(200_000, 2_000_000),
            "bidPrice": round(s["ltp"] - 0.05, 2),
            "askPrice": round(s["ltp"] + 0.05, 2),
        })
    return rows
