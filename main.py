"""
main.py
Headless console runner -- useful for quick testing without the
FastAPI server/dashboard. For the real deliverable, run server.py +
dashboard/index.html instead (see README.md).
"""
from data.symbols import SYMBOLS
from utils.symbol_state import SymbolState
from ml.backtest import TradeLogger
from ml.model import evaluate_trade
from settings import MOCK_MODE, POLL_INTERVAL_SECONDS
import time


def _fetch_quotes():
    if MOCK_MODE:
        from mock_data import get_mock_data
        return get_mock_data(SYMBOLS)
    from data.fetch import get_live_data
    return get_live_data(SYMBOLS)


def run():
    states = {s: SymbolState(s) for s in SYMBOLS}
    logger = TradeLogger()

    print("Running (mock mode)" if MOCK_MODE else "Running (LIVE Fyers data)")
    while True:
        for quote in _fetch_quotes():
            state = states[quote["symbol"]]
            event = state.on_quote(quote)
            if event:
                verdict = evaluate_trade(state, signal_is_buy=(event.signal.value == "BUY"))
                logger.on_crossover(event, state, verdict=verdict)
                print(f"{event.symbol}: {event.signal.value} @ {event.ltp} -> {verdict}")

        screened = [s.to_row() for s in states.values() if s.passes_screen()]
        print(f"-- {len(screened)}/{len(states)} symbols currently pass the screen --")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()