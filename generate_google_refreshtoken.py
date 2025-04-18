# generate_refresh_token.py

import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

# Load env vars
load_dotenv()

# Helper to fetch and validate required env vars
def get_env(var_name):
    val = os.getenv(var_name)
    if not val:
        raise ValueError(f"❌ Missing environment variable: {var_name}")
    return val

# Read and validate from .env
client_id = get_env("GOOGLE_CLIENT_ID")
client_secret = get_env("GOOGLE_CLIENT_SECRET")
auth_uri = get_env("GOOGLE_AUTH_URI")
token_uri = get_env("GOOGLE_TOKEN_URI")
redirect_uri = get_env("GOOGLE_REDIRECT_URI")

# Scopes required for Docs and Drive access
SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"]

# Client config
CLIENT_CONFIG = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": auth_uri,
        "token_uri": token_uri,
        "redirect_uris": [redirect_uri]
    }
}

# Run the OAuth flow
flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
creds = flow.run_local_server(port=0)

# Print the refresh token to be saved in .env
print("\n✅ Add this to your .env file:")
print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
