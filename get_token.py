"""
get_token.py
Step 2 of the Fyers OAuth flow: exchange the auth_code from login.py
for an access token.

Usage:
    export FYERS_AUTH_CODE="paste-the-code-here"
    python get_token.py

The auth_code is read from an environment variable, not hardcoded --
auth codes (and the resulting access tokens) are live credentials and
should never be committed, pasted into chat, or left in a file.
"""
import os
from fyers_apiv3 import fyersModel
from config import FYERS_CLIENT_ID, FYERS_SECRET_KEY, REDIRECT_URI

AUTH_CODE = os.environ.get("FYERS_AUTH_CODE", "")
if not AUTH_CODE:
    raise SystemExit("Set FYERS_AUTH_CODE in your environment first (see docstring).")

session = fyersModel.SessionModel(
    client_id=FYERS_CLIENT_ID,
    secret_key=FYERS_SECRET_KEY,
    redirect_uri=REDIRECT_URI,
    response_type="code",
    grant_type="authorization_code",
)
session.set_token(AUTH_CODE)
response = session.generate_token()
print(response)
print("\nCopy the access_token above into FYERS_ACCESS_TOKEN in your environment.")
