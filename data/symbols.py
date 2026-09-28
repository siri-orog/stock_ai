"""
data/symbols.py

Practical note on "scan ALL NSE-listed stocks": NSE has 2000+ listed
equities. Polling all of them via REST quotes() every few seconds is
not realistic -- it would blow through Fyers' API rate limits and make
each refresh cycle painfully slow. The standard engineering approach
(and what real screeners do) is to poll a curated universe of liquid,
actively-traded stocks -- illiquid penny stocks wouldn't pass the
bid/ask > 10,00,000 liquidity filter anyway, so excluding them from
the poll list doesn't lose anything the assignment actually needs.

This list covers ~50 liquid large/mid-cap NSE stocks spanning a wide
price range, so a healthy number will fall in the Rs 30-500 band at
any given time as prices move. The price + liquidity screen in
strategy/filters.py still runs dynamically on every poll -- this list
is just the pool it screens FROM, not a hardcoded shortcut around the
actual filtering logic.

To go further (poll the full NSE universe), download Fyers' symbol
master CSV (https://public.fyers.in/sym_details/NSE_CM.csv) and build
this list from that programmatically -- left as a documented upgrade
given today's submission deadline.
"""

SYMBOLS = [
    "NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ",
    "NSE:SBIN-EQ", "NSE:INFY-EQ", "NSE:ITC-EQ", "NSE:LT-EQ",
    "NSE:AXISBANK-EQ", "NSE:KOTAKBANK-EQ", "NSE:BAJFINANCE-EQ", "NSE:BHARTIARTL-EQ",
    "NSE:HINDUNILVR-EQ", "NSE:MARUTI-EQ", "NSE:SUNPHARMA-EQ", "NSE:TATASTEEL-EQ",
    "NSE:WIPRO-EQ", "NSE:ONGC-EQ", "NSE:NTPC-EQ", "NSE:POWERGRID-EQ",
    "NSE:COALINDIA-EQ", "NSE:IOC-EQ", "NSE:GAIL-EQ", "NSE:BPCL-EQ",
    "NSE:HINDALCO-EQ", "NSE:VEDL-EQ", "NSE:JSWSTEEL-EQ", "NSE:TATAMOTORS-EQ",
    "NSE:TATAPOWER-EQ", "NSE:PNB-EQ", "NSE:BANKBARODA-EQ", "NSE:CANBK-EQ",
    "NSE:IDFCFIRSTB-EQ", "NSE:FEDERALBNK-EQ", "NSE:SAIL-EQ", "NSE:NMDC-EQ",
    "NSE:NATIONALUM-EQ", "NSE:BHEL-EQ", "NSE:RECLTD-EQ", "NSE:PFC-EQ",
    "NSE:IRFC-EQ", "NSE:YESBANK-EQ", "NSE:IDEA-EQ", "NSE:SUZLON-EQ",
    "NSE:ZOMATO-EQ", "NSE:PAYTM-EQ", "NSE:INDUSINDBK-EQ", "NSE:ASHOKLEY-EQ",
    "NSE:MOTHERSON-EQ", "NSE:GMRINFRA-EQ",
]
