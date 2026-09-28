"""
server.py

The backend behind dashboard/index.html.

LIVE MODE flow:

1. Download/read complete NSE equity universe.
2. Fetch quotes for ALL NSE equity symbols.
3. Apply LTP filter: Rs 30 - Rs 500.
4. Fetch market depth ONLY for LTP-passed symbols.
5. Apply liquidity filter:
       Bid Quantity > 1,000,000
       AND
       Ask Quantity > 1,000,000
6. Keep liquidity-passed symbols as active watchlist.
7. Poll only the active watchlist every few seconds.
8. Update SMMA / crossover / ML state.
9. Serve dashboard rows as JSON (including ETQ 5/20/60min and
   average price 20/60min, per the assignment's requirements).

Run:
    uvicorn server:app --reload --port 8000
"""

import os
import threading
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from data.symbols import SYMBOLS
from utils.symbol_state import SymbolState
from ml.backtest import TradeLogger
from ml.model import evaluate_trade

from settings import (
    MOCK_MODE,
    POLL_INTERVAL_SECONDS,
    UNIVERSE_RESCAN_SECONDS,
)

from strategy.filters import (
    filter_stock,
    PRICE_MIN,
    PRICE_MAX,
)


# -------------------------------------------------------------------
# FastAPI
# -------------------------------------------------------------------

app = FastAPI(title="Stock AI Screener API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Global state
# -------------------------------------------------------------------

_states = {}
_active_symbols = set()
_latest_depth = {}
_latest_rows = []
_last_verdict = {}
_logger = TradeLogger()

_screening_stats = {
    "total_nse_symbols": 0,
    "quotes_received": 0,
    "ltp_pass": 0,
    "liquidity_pass": 0,
    "liquidity_fail": 0,
    "final_pass": 0,
    "last_scan_time": None,
}


# -------------------------------------------------------------------
# Seed historical data for a new symbol
# -------------------------------------------------------------------

def _seed_new_state(symbol: str) -> SymbolState:
    state = SymbolState(symbol)
    _states[symbol] = state

    try:
        if MOCK_MODE:
            from mock_data import get_mock_history
            closes = get_mock_history(symbol, minutes=130)
        else:
            from data.fetch import get_historical_closes
            closes = get_historical_closes(symbol, minutes=130)

            if closes:
                print(f"[seed] {symbol}: {len(closes)} closes, range {min(closes):.2f}-{max(closes):.2f}")
            else:
                print(f"[seed] {symbol}: NO HISTORICAL CLOSES")

            time.sleep(0.4)

        if closes:
            state.seed_history(closes)

    except Exception as exc:
        print(f"[seed] {symbol}: failed ({exc}), will build up live instead")

    return state


def _get_or_create_state(symbol: str) -> SymbolState:
    return _states.get(symbol) or _seed_new_state(symbol)


# -------------------------------------------------------------------
# Universe scan loop
# -------------------------------------------------------------------

def _universe_scan_loop():

    global _active_symbols
    global _latest_depth
    global _screening_stats

    while True:
        try:
            if MOCK_MODE:
                _active_symbols = set(SYMBOLS)
                _screening_stats = {
                    "total_nse_symbols": len(SYMBOLS),
                    "quotes_received": len(SYMBOLS),
                    "ltp_pass": len(SYMBOLS),
                    "liquidity_pass": len(SYMBOLS),
                    "liquidity_fail": 0,
                    "final_pass": len(SYMBOLS),
                    "last_scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                }

            else:
                from data.fetch import (
                    get_all_nse_equity_symbols,
                    get_quotes_batched,
                    get_market_depth,
                )

                all_nse_symbols = get_all_nse_equity_symbols()
                total_nse = len(all_nse_symbols)

                print()
                print("======================================")
                print("STARTING NSE UNIVERSE SCAN")
                print("======================================")
                print(f"[universe_scan] Total NSE equity symbols: {total_nse}")

                quotes = get_quotes_batched(all_nse_symbols, batch_size=50, delay_seconds=0.4)
                quotes_received = len(quotes)
                print(f"[universe_scan] Quotes received: {quotes_received}")

                price_ok = [
                    q for q in quotes
                    if q.get("ltp") and PRICE_MIN <= q["ltp"] <= PRICE_MAX
                ]
                price_ok_symbols = [q["symbol"] for q in price_ok]
                ltp_pass_count = len(price_ok_symbols)
                print(f"[universe_scan] LTP PASS: {ltp_pass_count}")

                print(f"[universe_scan] Fetching market depth for {ltp_pass_count} LTP-passed symbols...")
                depth_map = get_market_depth(price_ok_symbols, batch_size=50, delay_seconds=0.4)
                _latest_depth = depth_map.copy()

                in_band = set()
                liquidity_fail_count = 0
                liquidity_pass_symbols = []

                for q in price_ok:
                    symbol = q["symbol"]
                    d = depth_map.get(symbol, {})
                    bid_qty = d.get("bidQty", 0)
                    ask_qty = d.get("askQty", 0)

                    if filter_stock(q["ltp"], bid_qty, ask_qty):
                        in_band.add(symbol)
                        liquidity_pass_symbols.append(symbol)
                    else:
                        liquidity_fail_count += 1

                open_trade_symbols = set(_logger._open_trades.keys())
                _active_symbols = in_band | open_trade_symbols

                _screening_stats = {
                    "total_nse_symbols": total_nse,
                    "quotes_received": quotes_received,
                    "ltp_pass": ltp_pass_count,
                    "liquidity_pass": len(in_band),
                    "liquidity_fail": liquidity_fail_count,
                    "final_pass": len(_active_symbols),
                    "last_scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                }

                print()
                print("======================================")
                print("SCREENING SUMMARY")
                print("======================================")
                print(f"TOTAL NSE SYMBOLS : {total_nse}")
                print(f"QUOTES RECEIVED   : {quotes_received}")
                print(f"LTP PASS          : {ltp_pass_count}")
                print(f"LIQUIDITY PASS    : {len(in_band)}")
                print(f"LIQUIDITY FAIL    : {liquidity_fail_count}")
                print(f"FINAL PASS        : {len(_active_symbols)}")
                print("======================================")

        except Exception as exc:
            print(f"[universe_scan] error: {exc}")

        time.sleep(UNIVERSE_RESCAN_SECONDS)


# -------------------------------------------------------------------
# Fetch quotes for active symbols
# -------------------------------------------------------------------

def _fetch_quotes(symbols):
    if MOCK_MODE:
        from mock_data import get_mock_data
        return get_mock_data(symbols)
    else:
        from data.fetch import get_quotes_batched
        quotes = get_quotes_batched(symbols, batch_size=50, delay_seconds=0.4)
        for q in quotes:
            d = _latest_depth.get(q["symbol"], {})
            q["bidQty"] = d.get("bidQty", 0)
            q["askQty"] = d.get("askQty", 0)
        return quotes


# -------------------------------------------------------------------
# Fast polling loop
# -------------------------------------------------------------------

def _poll_loop():
    global _latest_rows

    while True:
        try:
            symbols = list(_active_symbols)

            if not symbols:
                print("[poll_loop] No active symbols yet.")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            quotes = _fetch_quotes(symbols)
            rows = []

            for quote in quotes:
                symbol = quote["symbol"]
                state = _get_or_create_state(symbol)

                event = state.on_quote(quote)

                if event is not None:
                    verdict = evaluate_trade(state, signal_is_buy=(event.signal.value == "BUY"))
                    _logger.on_crossover(event, state, verdict=verdict)
                    _last_verdict[symbol] = verdict

                if not state.passes_screen():
                    continue

                row = state.to_row()
                verdict = _last_verdict.get(
                    symbol,
                    {"probability": 0.5, "decision": "WAIT", "reason": "No crossover yet"},
                )

                # --------------------------------------------------
                # Full dashboard row -- NOW includes ETQ 5/20/60min
                # and average price 20/60min, which were being
                # computed internally but never sent to the frontend.
                # --------------------------------------------------
                rows.append({
                    "symbol": row["symbol"],
                    "ltp": row["ltp"],
                    "smma20": row["smma20"],
                    "smma120": row["smma120"],
                    "bidQty": row["bidQty"],
                    "askQty": row["askQty"],
                    "bidPrice": row["bidPrice"],
                    "askPrice": row["askPrice"],
                    "etq5m": row["etq_5m"],
                    "etq20m": row["etq_20m"],
                    "etq60m": row["etq_60m"],
                    "avgLtp20m": row["avg_ltp_20m"],
                    "avgLtp60m": row["avg_ltp_60m"],
                    "signal": state.signal_label(),
                    "confidence": verdict["probability"],
                    "decision": verdict["decision"],
                    "reason": verdict["reason"],
                })

            _latest_rows = rows

        except Exception as exc:
            print(f"[poll_loop] error: {exc}")

        time.sleep(POLL_INTERVAL_SECONDS)


# -------------------------------------------------------------------
# FastAPI startup
# -------------------------------------------------------------------

@app.on_event("startup")
def _start_background_threads():
    global _active_symbols

    if MOCK_MODE:
        _active_symbols = set(SYMBOLS)
        for symbol in SYMBOLS:
            _seed_new_state(symbol)
    else:
        print("[startup] LIVE MODE enabled.")
        print("[startup] Full NSE universe will be scanned.")

    threading.Thread(target=_universe_scan_loop, daemon=True, name="universe-scan-thread").start()
    threading.Thread(target=_poll_loop, daemon=True, name="poll-thread").start()


# -------------------------------------------------------------------
# API endpoints
# -------------------------------------------------------------------

@app.get("/api/signals")
def get_signals():
    return _latest_rows


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mock_mode": MOCK_MODE,
        "symbols_ever_tracked": len(_states),
        "active_watchlist_size": len(_active_symbols),
        "screening": _screening_stats,
    }


@app.get("/api/universe")
def universe():
    return sorted(_active_symbols)


@app.get("/api/screening")
def screening():
    """Total checked / LTP pass / liquidity pass-fail / final pass -- for
    the dashboard's screening-funnel display."""
    return _screening_stats


@app.get("/api/performance")
def performance():
    """Row-per-day summary from daily_performance.csv, for the
    dashboard's analysis page. Empty list if nothing recorded yet
    (run `python -m ml.daily_performance --date YYYY-MM-DD` first)."""
    import csv as _csv

    from ml.daily_performance import PERF_PATH

    if not os.path.exists(PERF_PATH):
        return []

    with open(PERF_PATH, newline="") as f:
        return list(_csv.DictReader(f))


@app.get("/api/evaluation/{trade_date}")
def evaluation(trade_date: str):
    """Model-vs-actual report for one day. Prefers a saved report file
    (from `python -m ml.evaluate --date ...`); computes fresh if none
    exists yet."""
    import json as _json

    from ml.evaluate import REPORT_DIR, evaluate_day

    report_path = os.path.join(REPORT_DIR, f"evaluation_report_{trade_date}.json")
    if os.path.exists(report_path):
        with open(report_path) as f:
            return _json.load(f)

    try:
        return evaluate_day(trade_date)
    except ValueError as exc:
        return {"error": str(exc)}


@app.get("/api/liquidity")
def liquidity():
    liquidity_symbols = []
    for symbol in sorted(_active_symbols):
        depth = _latest_depth.get(symbol, {})
        liquidity_symbols.append({
            "symbol": symbol,
            "bidQty": depth.get("bidQty", 0),
            "askQty": depth.get("askQty", 0),
        })
    return liquidity_symbols