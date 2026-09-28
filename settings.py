"""
settings.py

Runtime toggles for the backend -- separate from config.py, which
holds broker credentials only (keep that file out of anything you
share or submit).
"""

# True  -> use the built-in mock feed (mock_data.py), no API calls,
#          safe to run any time (outside market hours, while testing).
# False -> poll the real Fyers quotes() endpoint via data/fetch.py.
#          Set this False for your actual screen-recording submission.
MOCK_MODE = False

# How often (seconds) the backend polls for new quotes on the active watchlist.
POLL_INTERVAL_SECONDS = 5

# How often (seconds) to re-scan the tracked universe for price+liquidity
# screening. 90s keeps the dashboard feeling responsive without hammering
# the depth() endpoint, which only accepts one symbol per call.
UNIVERSE_RESCAN_SECONDS = 90
