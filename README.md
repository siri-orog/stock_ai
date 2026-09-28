# Stock AI Screener -- Assignment 1

## Architecture
- `server.py` -- FastAPI backend. Runs a background thread that polls quotes
  (real Fyers or mock, per `settings.py`), maintains persistent per-symbol
  state (`utils/symbol_state.py`), detects SMMA crossovers, logs completed
  trades for training, and serves the result as JSON at `/api/signals`.
- `dashboard/index.html` -- the frontend. Polls `/api/signals` and renders
  the live table + ticker (no more hardcoded seed data).
- `dashboard/app.py` -- the earlier Streamlit version, kept for reference
  but not the recommended path (Streamlit re-runs the whole script on every
  refresh, which fights against the persistent per-symbol state this
  assignment needs).

## Running it (mock mode -- no broker credentials needed)
```
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```
Then open `dashboard/index.html` directly in a browser. `settings.MOCK_MODE`
is `True` by default so you can see the whole pipeline working immediately.

## Going live
1. Rotate/regenerate your Fyers credentials first if they were ever shared
   or committed anywhere (`config.py` should never leave your machine).
2. Run `login.py` then `get_token.py` to get a fresh access token; put it
   in an environment variable, not hardcoded in `config.py`.
3. Set `settings.MOCK_MODE = False`.
4. Re-run `uvicorn server:app --reload --port 8000` during market hours.

## Training the ML model
`crossover_log.csv` accumulates automatically as real crossovers open and
close while the server runs. Once you have 30+ labeled trades (ideally with
both winners and losers):
```
python -m ml.model
```
This saves `crossover_model.joblib`, which `server.py` picks up automatically
on its next restart. Until a trained model exists, the dashboard shows
verdicts from a clearly-labeled rule-based heuristic instead of guessing.

## Notes on the assignment's real-time data requirement
Fyers' REST `quotes()` endpoint (used here) doesn't expose tick-level LTQ --
only cumulative day `volume`. This project derives ETQ/LTQ-equivalent figures
from the delta in `volume` between polls, which is an exact measure of
quantity traded in that interval. For true tick-by-tick LTQ, swap in the
Fyers WebSocket feed (`fyers_apiv3.FyersWebsocket.data_ws`) -- the rest of
the pipeline (`SymbolState`, SMMA, crossover detection, ML) doesn't need to
change, only the ingestion source.

## Packaging for submission
- Strip `config.py` of real credentials before submitting (use env vars).
- `pyinstaller server.py` (or a small launcher script) to produce the .exe.
- Record the screen capture with `MOCK_MODE = False` during market hours so
  the demo shows genuinely live NSE data as the assignment requires.
