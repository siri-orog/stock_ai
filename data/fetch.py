import os
import requests
from fyers_apiv3 import fyersModel
from config import FYERS_CLIENT_ID, ACCESS_TOKEN

_SYMBOL_MASTER_URL = "https://public.fyers.in/sym_details/NSE_CM.csv"

_SYMBOL_MASTER_CACHE = os.path.join(
    os.path.dirname(__file__),
    "nse_symbols.csv"
)

# ✅ MUST ADD THIS
fyers = fyersModel.FyersModel(
    client_id=FYERS_CLIENT_ID,
    token=ACCESS_TOKEN,
    log_path=""
)

def get_live_data(symbols):
    data = {
        "symbols": ",".join(symbols)
    }

    try:
        response = fyers.quotes(data=data)

        # IMPORTANT: print the complete raw Fyers response
        print("\n========== FYERS QUOTES DEBUG ==========")
        print("Symbols:", symbols)
        print("Response:", response)
        print("========================================\n")

    except Exception as exc:
        print("\n========== FYERS QUOTES EXCEPTION ==========")
        print(exc)
        print("=============================================\n")
        return []

    output = []

    if response.get("s") == "ok":
        for item in response.get("d", []):
            symbol = item.get("n", "N/A")
            values = item.get("v", {})

            lp = values.get("lp", 0)
            volume = values.get("volume", 0)

            bid_price = values.get("bid", 0)
            ask_price = values.get("ask", 0)

            output.append({
                "symbol": symbol,
                "ltp": lp,
                "volume": volume,
                "bidQty": 0,
                "askQty": 0,
                "bidPrice": bid_price,
                "askPrice": ask_price,
            })

    else:
        print(
            f"[get_live_data] Fyers quotes failed: "
            f"{response}"
        )

    return output


def get_market_depth(symbols, batch_size=50, delay_seconds=0.4):
    """Fetches real bid/ask QUANTITY via Fyers' market depth endpoint.

    quotes() only returns bid/ask PRICE, not quantity -- there's no
    quantity field in that response at all. Market depth is a
    separate call. Returns {symbol: {"bidQty": int, "askQty": int}}.

    NOTE: the exact response field names here are my best-informed
    guess (Fyers commonly uses totalbuyqty/totalsellqty for the
    aggregate depth quantities NSE calls "Total Buy Qty"/"Total Sell
    Qty" -- which is almost certainly what the assignment's
    "Bid Quantity"/"Ask Quantity" > 10,00,000 threshold refers to,
    since that number only makes sense at the aggregate level, not a
    single best-bid level). This is looked up case-insensitively with
    several fallback names since it hasn't been verified against a
    real response yet -- if it comes back empty, print the raw
    response for one symbol and fix the exact key here.
    """
    import time as _time

    result = {}
    for symbol in symbols:
        data = {"symbol": symbol, "ohlcv_flag": "0"}  # depth() takes ONE symbol per call, not comma-separated
        try:
            response = fyers.depth(data=data)
            print("\n========== FYERS DEPTH DEBUG ==========")
            print("Symbol:", symbol)
            print("Raw response:", response)
            print("=======================================\n")
        except Exception as exc:
            print(f"[get_market_depth] request failed for {symbol}: {exc}")
            response = {}

        if response.get("s") == "ok":
            depth_data = response.get("d", {})
            entry = depth_data.get(symbol, depth_data)  # some responses key by symbol, some don't
            lowered = {k.lower(): v for k, v in entry.items()} if isinstance(entry, dict) else {}
            bid_qty = (
                lowered.get("totalbuyqty")
                or lowered.get("totalbuyquantity")
                or lowered.get("bidqty")
                or 0
            )
            ask_qty = (
                lowered.get("totalsellqty")
                or lowered.get("totalsellquantity")
                or lowered.get("askqty")
                or 0
            )
            result[symbol] = {"bidQty": bid_qty, "askQty": ask_qty}
        else:
            print(f"[get_market_depth] {symbol}: {response}")

        _time.sleep(delay_seconds)

    return result


def get_historical_closes(symbol, minutes=130):
    import time
    from datetime import datetime, timedelta
    from fyers_apiv3 import fyersModel
    from config import FYERS_CLIENT_ID, ACCESS_TOKEN

    try:
        fyers = fyersModel.FyersModel(
            client_id=FYERS_CLIENT_ID,
            token=ACCESS_TOKEN,
            log_path=""
        )

        # Get latest available trading day
        today = datetime.now()

        # Look back several days so weekends/holidays are handled
        for days_back in range(1, 8):

            target_date = today - timedelta(days=days_back)

            date_str = target_date.strftime("%Y-%m-%d")

            range_from = int(
                time.mktime(
                    time.strptime(
                        f"{date_str} 09:15:00",
                        "%Y-%m-%d %H:%M:%S"
                    )
                )
            )

            range_to = int(
                time.mktime(
                    time.strptime(
                        f"{date_str} 15:30:00",
                        "%Y-%m-%d %H:%M:%S"
                    )
                )
            )

            data = {
                "symbol": symbol,
                "resolution": "1",
                "date_format": "0",
                "range_from": str(range_from),
                "range_to": str(range_to),
                "cont_flag": "1"
            }

            response = fyers.history(data=data)

            candles = response.get("candles", [])

            if candles:
                print(
                    f"[history] {symbol}: "
                    f"{len(candles)} candles loaded from {date_str}"
                )

                # IMPORTANT:
                # Keep only candles with actual traded volume
                valid_candles = [
                    c for c in candles
                    if len(c) >= 6 and c[5] > 0
                ]

                print(
                    f"[history] {symbol}: "
                    f"{len(valid_candles)} candles after volume filter"
                )

                # Extract CLOSE prices only
                closes = [c[4] for c in valid_candles]

                # Return requested number of latest valid closes
                return closes[-minutes:]

        print(f"[history] {symbol}: No historical data found")
        return []

    except Exception as e:
        print(f"[get_historical_closes] {symbol}: ERROR: {e}")
        return []

def get_all_nse_equity_symbols(force_refresh=False):
    """Downloads Fyers' NSE Capital Market symbol master (cached to
    disk, since the instrument list barely changes intraday -- no
    need to redownload every poll cycle) and returns every equity
    ticker in "NSE:XXXX-EQ" format.

    The exact column layout of Fyers' CSV isn't guaranteed stable, so
    this scans every field of every row with a regex instead of
    trusting a fixed column index -- more robust to format changes.
    """
    import csv
    import re

    if force_refresh or not os.path.exists(_SYMBOL_MASTER_CACHE):
        resp = requests.get(_SYMBOL_MASTER_URL, timeout=30)
        resp.raise_for_status()
        with open(_SYMBOL_MASTER_CACHE, "w", encoding="utf-8") as f:
            f.write(resp.text)

    symbols = set()
    pattern = re.compile(r"^NSE:[A-Z0-9&\-]+-EQ$")
    with open(_SYMBOL_MASTER_CACHE, encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            for field in row:
                field = field.strip()
                if pattern.match(field):
                    symbols.add(field)

    return sorted(symbols)


def get_quotes_batched(symbols, batch_size=50, delay_seconds=0.4):
    """fyers.quotes() only accepts a limited number of symbols per
    call (observed practical limit ~50) -- this chunks a large symbol
    list into batches and merges the results, reusing get_live_data's
    parsing for each chunk.

    delay_seconds pauses between batches -- without this, scanning a
    large universe (e.g. 2000+ NSE symbols = ~50 batches) fires all
    calls back-to-back and trips Fyers' rate limiter (429 errors),
    which can also surface as spurious "invalid token" responses when
    requests arrive faster than the gateway can process them.
    """
    import time as _time

    all_rows = []
    for i in range(0, len(symbols), batch_size):
        chunk = symbols[i:i + batch_size]
        all_rows.extend(get_live_data(chunk))
        if i + batch_size < len(symbols):  # no need to sleep after the last batch
            _time.sleep(delay_seconds)
    return all_rows
