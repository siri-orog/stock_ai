"""
test_api.py
Quick manual sanity check that your Fyers credentials/token work and
quotes are flowing -- not part of the main pipeline (server.py is).
"""
import time
from fyers_apiv3 import fyersModel
from config import FYERS_CLIENT_ID, ACCESS_TOKEN

fyers = fyersModel.FyersModel(client_id=FYERS_CLIENT_ID, token=ACCESS_TOKEN, log_path="")

symbols = ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:TCS-EQ"]

while True:
    response = fyers.quotes(data={"symbols": ",".join(symbols)})
    print("\nLive Market Data\n")
    if response.get("s") == "ok":
        for stock in response["d"]:
            print(f"{stock['n']} -> Rs {stock['v']['lp']}")
    else:
        print(response)
    time.sleep(5)
