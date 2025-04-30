# generate_refresh_token.py

import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from urllib.parse import urlparse, parse_qs  # Added for URL parsing

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
redirect_uri = get_env("GOOGLE_REDIRECT_URI") # Make sure this matches the one in Google Cloud Console

# Scopes required for Docs and Drive access
SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"]

# Client config
CLIENT_CONFIG = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": auth_uri,
        "token_uri": token_uri,
        "redirect_uris": [redirect_uri] # The script needs this even if we don't run a server
    }
}

# --- Manual OAuth Flow ---
flow = InstalledAppFlow.from_client_config(
    CLIENT_CONFIG,
    SCOPES,
    redirect_uri=redirect_uri # Explicitly pass redirect_uri here
)

# 1. Generate and print the authorization URL
auth_url, _ = flow.authorization_url(prompt='consent') # prompt='consent' forces approval screen
print('--- Step 1 ---')
print('Please send this URL to your client and ask them to authorize:')
print(f"{auth_url}\n")
print('--- Step 2 ---')
print('Ask the client to copy the FULL URL they are redirected to after authorization (it might show an error, that\'s OK).')

# 2. Get the full redirect URL from the user (copied from client)
redirect_response_url = input('Paste the full redirect URL here: ')

# 3. Parse the authorization code from the redirect URL
try:
    # This replaces the local server interaction and fetches token directly
    flow.fetch_token(authorization_response=redirect_response_url)
    creds = flow.credentials
except Exception as e:
    print(f"\n❌ Failed to fetch token from the provided URL: {e}")
    print("Please ensure you pasted the complete URL including the 'code=' part.")
    exit() # Exit if token fetch fails

# 4. Print the refresh token
if creds and creds.refresh_token:
    print("\n✅ Success! Add this to your .env file:")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
else:
    print("\n❌ Could not obtain refresh token. Make sure the client granted offline access.")
    print("Credentials obtained:", creds) # Print whatever creds we got for debugging
