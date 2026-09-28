"""
login.py
Step 1 of the Fyers OAuth flow: open the printed URL, log in, and copy
the `auth_code` from the redirected URL's query string -- you'll paste
it into an environment variable for get_token.py (never into a file).
"""
from fyers_apiv3 import fyersModel
from config import FYERS_CLIENT_ID, REDIRECT_URI

session = fyersModel.SessionModel(
    client_id=FYERS_CLIENT_ID,
    redirect_uri=REDIRECT_URI,
    response_type="code",
    grant_type="authorization_code",
)

response = session.generate_authcode()
print("Open this URL in your browser, log in, then copy the auth_code")
print("from the redirected URL's query string:\n")
print(response)
