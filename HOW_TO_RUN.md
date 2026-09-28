# How to Run This Project

## 1. One-time setup

```
cd D:\stock_ai
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Every time you want to run it

### Step 1 — Open a terminal and go to the project folder
```
cd D:\stock_ai
```

### Step 2 — Activate the virtual environment
```
venv\Scripts\activate
```
You should see `(venv)` appear at the start of your terminal line.

### Step 3 — Start the backend server
```
uvicorn server:app --reload --port 8000
```
Wait for this line, with no errors above it:
```
INFO:     Application startup complete.
```
**Leave this terminal open. Do not close it or press Ctrl+C** unless you
actually want to restart — restarting resets all SMMA progress back to
zero (SMMA20 needs ~20 min of continuous runtime, SMMA120 needs ~2 hours).

### Step 4 — Confirm the backend is alive
In a browser tab, open:
```
http://127.0.0.1:8000/api/health
```
You should see:
```
{"status":"ok","mock_mode":true,"symbols_tracked":4}
```

### Step 5 — Open the dashboard
Option A (VS Code): open `dashboard/index.html`, click "Go Live" (bottom-right).
Option B (command line, no extension needed):
```
cd dashboard
python -m http.server 5500
```
Then open `http://127.0.0.1:5500/index.html` in your browser.

## 3. Switching to live Fyers data (do this during NSE market hours, 9:15am-3:30pm IST)

1. Set your credentials as environment variables (never hardcode them):
   ```
   set FYERS_CLIENT_ID=your-client-id
   set FYERS_SECRET_KEY=your-secret-key
   set FYERS_REDIRECT_URI=http://127.0.0.1/
   ```
2. Run `python login.py`, open the printed URL, log in, copy the `auth_code`
   from the redirected URL.
3. `set FYERS_AUTH_CODE=the-code-you-copied`
4. Run `python get_token.py` — copy the `access_token` it prints.
5. `set FYERS_ACCESS_TOKEN=the-access-token`
6. Open `settings.py` and change `MOCK_MODE = False`.
7. Restart the server (Step 3 above).

## 4. Training the ML model (once you have real trading data)

Let the server run for several days during market hours so `crossover_log.csv`
accumulates 30+ labeled trades (both wins and losses). Then:
```
python -m ml.model
```
This saves `crossover_model.joblib`. Restart the server (Step 3) so it picks
up the trained model instead of the rule-based heuristic fallback.

### NSE symbols total
python -c "from data.fetch import get_all_nse_equity_symbols; s=get_all_nse_equity_symbols(); print('TOTAL NSE EQUITY SYMBOLS:', len(s))"
### Ltp passed
python -c "from data.fetch import get_all_nse_equity_symbols,get_quotes_batched; s=get_all_nse_equity_symbols(); q=get_quotes_batched(s); p=[x for x in q if 30 <= float(x.get('ltp',0)) <= 500]; print('TOTAL NSE:',len(s)); print('QUOTES RECEIVED:',len(q)); print('LTP 30-500 PASS:',len(p)); print('LTP FAIL:',len(q)-len(p))"
### Liquidity passed
python test_liquidity.py
### To know the total count of label 
python -c "import pandas as pd; df = pd.read_csv('crossover_log.csv'); print('Total rows:', len(df)); print(df['label'].value_counts())"
### To know todays count of label
python -c "import pandas as pd; df = pd.read_csv('crossover_log.csv'); today = df[df['trade_date']=='2026-08-20']; print('Today rows:', len(today)); print(today['label'].value_counts())"
### To evaluate 
python -m ml.evaluate --date 2026-08-18
### Daily performance
python -m ml.daily_performance --date 2026-08-18