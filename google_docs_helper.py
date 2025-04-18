# google_docs_helper.py

import os
from typing import List
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request # <--- ADD THIS LINE
# Import the Resource type for hinting (optional but good practice)
from googleapiclient.discovery import Resource

# ... rest of your code

load_dotenv(override=True)

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']

# --- Environment Variable Check (Optional but Recommended) ---
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_TOKEN_URI = os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token") # Default URI
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

if not all([GOOGLE_REFRESH_TOKEN, GOOGLE_TOKEN_URI, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]):
    raise ValueError("Missing required Google API credentials in .env file.")
# --- End Check ---

def get_docs_service() -> Resource | None:
    """Authenticate and return Google Docs API service using .env credentials."""
    try:
        creds = Credentials(
            token=None, # No initial access token, use refresh token
            refresh_token=GOOGLE_REFRESH_TOKEN,
            token_uri=GOOGLE_TOKEN_URI,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES
        )
        # Check if credentials are valid and refresh if necessary *before* building service
        # This helps catch RefreshError earlier.
        if not creds.valid:
             creds.refresh(Request()) # Requires: from google.auth.transport.requests import Request

        service = build('docs', 'v1', credentials=creds)
        print("✅ Google Docs service created successfully.")
        return service
    except RefreshError as e:
        print(f"❌ Error refreshing Google credentials: {e}")
        print("   Please ensure your GOOGLE_REFRESH_TOKEN is valid and hasn't been revoked.")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during authentication: {e}")
        return None


def append_lines_to_google_doc(document_id: str, lines: List[str]):
    """Appends lines of text to the end of the Google Doc without touching existing content."""
    service = get_docs_service()
    if not service:
        print("❌ Cannot proceed without a valid Google Docs service.")
        return

    try:
        # Get current document to find the end index. Only request necessary fields.
        doc = service.documents().get(
            documentId=document_id,
            fields='body(content(endIndex))' # Optimize payload - only need endIndex
        ).execute()

        body_content = doc.get('body', {}).get('content')

        # Determine insertion index:
        # Default to 1 (start) if doc is empty or has no structural content.
        # Otherwise, insert just before the final newline of the last content element.
        insert_index = 1
        if body_content:
            # Get the endIndex of the very last structural element
            last_element_end_index = body_content[-1]['endIndex']
            # Insert *before* the final implicit newline character
            insert_index = last_element_end_index - 1
            # Ensure index is never less than 1
            insert_index = max(1, insert_index)

        # Combine all lines into one text block with newline separators
        # Prepend \n to ensure it starts on a new line after existing content.
        # Append \n to ensure the *next* append will start on a new line.
        text_block = '\n' + '\n'.join(lines) + '\n'

        requests = [
            {
                'insertText': {
                    'location': {'index': insert_index},
                    'text': text_block
                }
            }
        ]

        service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()

        print(f"✅ Text successfully appended to document ID: {document_id}")

    except HttpError as error:
        print(f"❌ An API error occurred: {error}")
        details = error.resp.get('content', '{}')
        print(f"   Error details: {details}")
    except IndexError:
         # This might occur if the document structure is very unusual,
         # though the refined index logic aims to prevent it.
        print(f"❌ Could not determine insertion point. Document structure might be empty or unusual.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")


# --- Example Usage ---
if __name__ == "__main__":
    TARGET_DOCUMENT_ID = "12RzrqWU-ppj5uoQdY3S7_0KTXhBFnJ0Gzrz7N0kVAoU" # <<< CHANGE THIS

    if TARGET_DOCUMENT_ID == "YOUR_DOCUMENT_ID_HERE":
        print("⚠️ Please replace 'YOUR_DOCUMENT_ID_HERE' with your actual Google Doc ID.")
    else:
        lines_to_add = [
            "This is the first line to append.",
            "This is the second line.",
            f"Timestamp: {os.times().user}" # Example dynamic content
        ]
        append_lines_to_google_doc(TARGET_DOCUMENT_ID, lines_to_add)
