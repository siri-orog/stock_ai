from data.fetch import get_all_nse_equity_symbols, get_quotes_batched, get_market_depth

# 1. Get all NSE symbols
symbols = get_all_nse_equity_symbols()

print("TOTAL NSE SYMBOLS:", len(symbols))

# 2. Get LTP for all symbols
print("\nGetting LTP data...")
quotes = get_quotes_batched(symbols)

# 3. Keep only LTP ₹30–₹500
ltp_pass = []

for row in quotes:
    ltp = row.get("ltp", 0)

    if 30 <= ltp <= 500:
        ltp_pass.append(row["symbol"])

print("LTP ₹30–₹500 PASS:", len(ltp_pass))

# 4. Get market depth for LTP-passed symbols
print("\nGetting market depth...")
depth = get_market_depth(
    ltp_pass,
    batch_size=50,
    delay_seconds=0.4
)

# 5. Apply liquidity filter
liquidity_pass = []

for symbol in ltp_pass:
    d = depth.get(symbol, {})

    bid_qty = d.get("bidQty", 0)
    ask_qty = d.get("askQty", 0)

    if bid_qty > 1_000_000 and ask_qty > 1_000_000:
        liquidity_pass.append(symbol)

# 6. Final result
print("\n======================================")
print("SCREENING SUMMARY")
print("======================================")
print("TOTAL NSE SYMBOLS :", len(symbols))
print("LTP PASS          :", len(ltp_pass))
print("LIQUIDITY PASS    :", len(liquidity_pass))
print("LIQUIDITY FAIL    :", len(ltp_pass) - len(liquidity_pass))
print("FINAL PASS        :", len(liquidity_pass))
print("======================================")

print("\nLIQUIDITY-PASS SYMBOLS:")

for symbol in liquidity_pass:
    print(symbol)