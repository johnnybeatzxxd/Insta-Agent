import re
from datetime import datetime
from typing import List, Dict, Any, Optional # Use Optional instead of | for broader compatibility

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource # Import Resource
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request

import os
load_dotenv(override=True)

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']

# --- Environment Variables ---
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_TOKEN_URI = os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
DOC_ID = os.getenv("GOOGLE_DOC_ID")

if not all([GOOGLE_REFRESH_TOKEN, GOOGLE_TOKEN_URI, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]):
    print("⚠️ Missing required Google API credentials in .env file. Please check your .env")
    # Consider exiting or raising an error depending on your application's needs
    # raise ValueError("Missing required Google API credentials in .env file.")

# --- Authentication (Your existing function is good) ---
def get_docs_service() -> Optional[Resource]:
    """Authenticate and return Google Docs API service using .env credentials."""
    creds = None
    # Load token if exists
    token_path = 'token.json' # Define path for token file
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
             print(f"Warning: Could not load existing token file '{token_path}': {e}")

    # If no valid credentials, try refreshing or getting new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Credentials expired, attempting refresh...")
            try:
                creds.refresh(Request())
                print("✅ Credentials refreshed successfully.")
            except RefreshError as e:
                print(f"❌ Error refreshing Google credentials: {e}")
                print("   Refresh token might be invalid or revoked. Trying to use configured refresh token...")
                # Fallback to using .env refresh token if loaded token fails
                creds = None # Reset creds to force use of .env refresh token
            except Exception as e:
                 print(f"❌ Unexpected error during credential refresh: {e}")
                 return None

        # If refresh failed or no token existed, use .env credentials
        if not creds or not creds.valid:
             print("Attempting authentication using .env credentials...")
             if not all([GOOGLE_REFRESH_TOKEN, GOOGLE_TOKEN_URI, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]):
                 print("❌ Cannot authenticate: Missing required Google API credentials in .env file.")
                 return None
             try:
                 creds = Credentials(
                     token=None,
                     refresh_token=GOOGLE_REFRESH_TOKEN,
                     token_uri=GOOGLE_TOKEN_URI,
                     client_id=GOOGLE_CLIENT_ID,
                     client_secret=GOOGLE_CLIENT_SECRET,
                     scopes=SCOPES
                 )
                 # Initial refresh is necessary when using refresh token directly
                 creds.refresh(Request())
                 print("✅ Authenticated successfully using .env credentials.")
             except RefreshError as e:
                 print(f"❌ Error refreshing using .env credentials: {e}")
                 print("   Please ensure your GOOGLE_REFRESH_TOKEN in .env is valid.")
                 return None
             except Exception as e:
                 print(f"❌ An unexpected error occurred during .env authentication: {e}")
                 return None

        # Save the credentials for the next run
        try:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            print(f"Credentials saved to {token_path}")
        except Exception as e:
             print(f"Warning: Could not save token file '{token_path}': {e}")


    # Build and return the service
    try:
        service = build('docs', 'v1', credentials=creds)
        print("✅ Google Docs service created successfully.")
        return service
    except Exception as e:
        print(f"❌ Failed to build Google Docs service: {e}")
        return None


# --- Helper Functions (Adapted from Pure Python) ---

def get_paragraph_text(paragraph: Dict[str, Any]) -> str:
    """Extracts the text content from a paragraph element."""
    text = ""
    elements = paragraph.get('elements', [])
    for element in elements:
        text_run = element.get('textRun')
        if text_run and 'content' in text_run:
            text += text_run['content']
    return text.strip()

def parse_date_heading_from_line(line: str, target_year: int) -> Optional[datetime.date]:
    """Parses a date from a line matching 'Month Day Weekday'. Assumes target_year."""
    pattern = re.compile(
        r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*$",
        re.IGNORECASE
    )
    match = pattern.match(line.strip())
    if match:
        month_str, day_str, _ = match.groups()
        try:
            date_str_with_year = f"{month_str} {day_str} {target_year}"
            parsed_dt = datetime.strptime(date_str_with_year, "%B %d %Y")
            return parsed_dt.date()
        except ValueError:
            return None
    return None

def format_appointment_line(appointment_details: Dict[str, Any]) -> Optional[str]:
    """
    Formats the appointment dictionary into a string line using the new format,
    including the appointment ID at the end.
    Example: Giselle Rodriguez - 1:30pm Lash Lift ($20/100) (ID: xyz789)
    RETURNS THE LINE *WITHOUT* A TRAILING NEWLINE.
    """
    try:
        # --- Extract data ---
        name = appointment_details.get('name', 'N/A')
        iso_dt_str = appointment_details.get('date_time')
        if not iso_dt_str:
            raise ValueError("Missing 'date_time' in appointment_details")
        dt_obj = datetime.fromisoformat(iso_dt_str)

        # Extract new keys and handle potential '$' sign
        deposit_raw = appointment_details.get('deposit', '')
        deal_price_raw = appointment_details.get('deal_price', '')
        service = appointment_details.get('service', '').strip() # Remove leading/trailing spaces
        appointment_id = appointment_details.get('appointment_id') # Get the appointment ID

        # Clean up potential '$' signs (more robustly)
        deposit = str(deposit_raw).replace('$', '').strip()
        deal_price = str(deal_price_raw).replace('$', '').strip()

        # --- Format Time ---
        time_str = dt_obj.strftime("%-I:%M%p").lower() # Use %l on Linux/macOS if -I fails
        if time_str == "12:00pm": time_str = "12nn"
        elif time_str.startswith("0"): time_str = time_str[1:]

        # --- Combine based on new format ---
        appointment_line = f"{name} - {time_str}"

        # Add service if it exists
        if service:
            appointment_line += f" {service}"

        # Add deposit/deal_price part if both exist
        if deposit and deal_price:
            appointment_line += f" (${deposit}/{deal_price})"
        elif deposit: # Handle case if only deposit is provided
             appointment_line += f" (${deposit} deposit)"
        elif deal_price: # Handle case if only deal_price is provided
             appointment_line += f" (${deal_price})"

        # Add appointment ID if it exists
        if appointment_id:
            appointment_line += f" (ID: {appointment_id})"

        # *** RETURN WITHOUT TRAILING NEWLINE ***
        return appointment_line.strip() # Ensure no trailing space if service/price/id is missing

    except Exception as e:
        print(f"❌ Error formatting appointment line: {e}")
        print(f"   Details: {appointment_details}")
        return None

# --- Core Logic: Insert Appointment using API ---
def add_appointment_to_google_doc(new_appointment_details,document_id=DOC_ID):
    """
    Finds the correct date location in a Google Doc and inserts the new appointment
    using the Google Docs API, ensuring single blank line spacing and styling.
    """
    service = get_docs_service()
    # ... (rest of the initial setup, getting service, processing appointment details) ...
    try:
        # 1. Process New Appointment Info
        target_iso_dt = new_appointment_details.get('date_time')
        if not target_iso_dt: raise ValueError("Missing 'date_time'")
        target_dt = datetime.fromisoformat(target_iso_dt)
        target_date = target_dt.date()
        target_year = target_dt.year
        target_date_heading_str = target_dt.strftime("%B %d %A")
        formatted_appointment_line = format_appointment_line(new_appointment_details)
        if not formatted_appointment_line: return False

        # 2. Get Document Content
        print(f"Fetching content for document: {document_id}")
        document = service.documents().get(
            documentId=document_id,
            fields='body(content(startIndex,endIndex,paragraph(elements(textRun(content,textStyle)))))'
            ).execute()
        content = document.get('body', {}).get('content', [])
        print(f"Document contains {len(content)} structural elements.")

        # 3. Scan for Date Headings & Find Document End
        found_dates = []
        last_content_end_index = 1
        if content:
             last_element = content[-1]
             last_content_end_index = last_element.get('endIndex', 1)
        print(f"Calculated last content end index: {last_content_end_index}")

        for i, element in enumerate(content):
            # ... (date scanning logic remains the same) ...
            if element.get('paragraph'):
                para_text = get_paragraph_text(element['paragraph'])
                parsed_date = parse_date_heading_from_line(para_text, target_year)
                if parsed_date:
                    start_idx = element.get('startIndex')
                    end_idx = element.get('endIndex')
                    if start_idx is not None and end_idx is not None:
                        found_dates.append({
                            'date': parsed_date, 'startIndex': start_idx,
                            'endIndex': end_idx, 'text': para_text, 'contentIndex': i
                        })

        found_dates.sort(key=lambda x: x['date'])

        # 4. Determine Insertion Logic and Index
        requests = []
        date_heading_found = False
        target_date_info = None

        for date_info in found_dates:
            if date_info['date'] == target_date:
                date_heading_found = True; target_date_info = date_info; break

        if date_heading_found:
            # --- Append Appointment to Existing Date ---
            print(f"Found existing date heading: '{target_date_info['text']}'")
            # ... (logic to find insertion_index remains the same) ...
            insertion_index = target_date_info['endIndex'] # Start after heading
            current_content_idx = target_date_info['contentIndex'] + 1
            next_heading_start_index = -1
            for i, date_info in enumerate(found_dates):
                 if date_info['startIndex'] > target_date_info['startIndex']:
                      next_heading_start_index = date_info['startIndex']; break
            while current_content_idx < len(content):
                element = content[current_content_idx]; el_start_index = element.get('startIndex')
                if el_start_index is None: current_content_idx += 1; continue
                if next_heading_start_index != -1 and el_start_index >= next_heading_start_index: break
                if element.get('paragraph'):
                    para_text = get_paragraph_text(element['paragraph'])
                    if parse_date_heading_from_line(para_text, target_year): break
                insertion_index = element.get('endIndex', insertion_index); current_content_idx += 1

            # Final index adjustment for API
            adjusted_appointment_index = insertion_index
            if adjusted_appointment_index >= last_content_end_index and last_content_end_index > 1:
                print(f"Adjusting APPOINTMENT insertion index from {adjusted_appointment_index} to {last_content_end_index - 1}")
                adjusted_appointment_index = last_content_end_index - 1
            elif adjusted_appointment_index < 1: adjusted_appointment_index = 1

            # --- INSERTION LOGIC FOR APPENDING ---
            # Always need a newline before appending appointment
            # Add an EXTRA newline AFTER the appointment for spacing
            appointment_text_to_insert = "\n" + formatted_appointment_line + "\n\n"
            appt_start_index = adjusted_appointment_index
            appt_end_index = appt_start_index + len(appointment_text_to_insert)

            # 1. Insert Appointment Text
            requests.append({'insertText': {'location': {'index': appt_start_index}, 'text': appointment_text_to_insert}})
            # 2. Unbold Appointment Text (adjust range for added newlines)
            requests.append({
                'updateTextStyle': {
                    'range': { 'startIndex': appt_start_index + 1, 'endIndex': appt_end_index - 2 }, # Range is just the appointment text
                    'textStyle': { 'bold': False }, 'fields': 'bold' }})

        else:
            # --- Insert New Date Heading + Appointment ---
            print(f"Date heading '{target_date_heading_str}' not found. Inserting new heading.")
            new_heading_text_line = target_date_heading_str # Base heading text

            # ... (logic to find heading_insertion_index remains the same) ...
            heading_insertion_index = -1; found_spot = False
            for date_info in found_dates:
                if date_info['date'] > target_date: heading_insertion_index = date_info['startIndex']; found_spot = True; break
            if not found_spot: heading_insertion_index = last_content_end_index

            # Final index adjustment for API
            adjusted_heading_index = heading_insertion_index
            if adjusted_heading_index >= last_content_end_index and last_content_end_index > 1:
                 print(f"Adjusting HEADING insertion index from {adjusted_heading_index} to {last_content_end_index - 1}")
                 adjusted_heading_index = last_content_end_index - 1
            elif adjusted_heading_index < 1: adjusted_heading_index = 1

            # --- INSERTION LOGIC FOR NEW DATE ---
            # 1. Insert Heading
            prefix = "\n" if adjusted_heading_index > 1 else "" # Single newline prefix if not at start
            # Heading ends with TWO newlines for spacing before first appointment
            heading_text_to_insert = prefix + new_heading_text_line + "\n\n"
            heading_start_index = adjusted_heading_index
            heading_end_index = heading_start_index + len(heading_text_to_insert)
            requests.append({'insertText': {'location': {'index': heading_start_index}, 'text': heading_text_to_insert}})

            # 2. Bold Heading (adjust range for added newlines)
            requests.append({
                'updateTextStyle': {
                    'range': { 'startIndex': heading_start_index + len(prefix), 'endIndex': heading_end_index - 2 }, # Range is just the heading text
                    'textStyle': { 'bold': True }, 'fields': 'bold' }})

            # 3. Insert First Appointment
            # Appointment text just needs trailing newline, inserts right after heading's newline
            # Suffix changed for consistency - add extra \n after first appointment too
            appointment_text_to_insert = formatted_appointment_line + "\n\n"
            appointment_insertion_index = heading_end_index # Start right after heading
            appt_start_index = appointment_insertion_index
            appt_end_index = appt_start_index + len(appointment_text_to_insert)
            requests.append({'insertText': {'location': {'index': appt_start_index}, 'text': appointment_text_to_insert}})

            # 4. Unbold Appointment (adjust range for added newlines)
            requests.append({
                'updateTextStyle': {
                    'range': { 'startIndex': appt_start_index, 'endIndex': appt_end_index - 2 }, # Range is appointment text
                    'textStyle': { 'bold': False }, 'fields': 'bold' }})

        # 5. Execute Batch Update
        # ... (rest of the function remains the same: execution, error handling) ...
        if requests:
            print(f"Preparing to send {len(requests)} requests...")
            # print(f"Requests: {requests}") # Uncomment for detailed debugging
            body = {'requests': requests}
            service.documents().batchUpdate(documentId=document_id, body=body).execute()
            print(f"✅ Successfully added/updated appointment for {target_date_heading_str} in doc ID: {document_id}")
            return True
        else:
            print("⚠️ No update requests generated.")
            return False

    except HttpError as error:
        # ... error handling ...
        print(f"❌ An API error occurred: {error}")
        try:
            error_content = error.resp.get('content', b'{}').decode('utf-8')
            import json
            details = json.loads(error_content); print(f"   Error details: {details.get('error', {}).get('message', 'No details provided')}")
        except Exception as json_err:
            print(f"   Could not parse error details JSON: {json_err}"); print(f"   Raw error content: {error.resp.get('content')}")
        return False
    except Exception as e:
        # ... error handling ...
        print(f"❌ An unexpected error occurred: {e}")
        import traceback; traceback.print_exc()
        return False

# --- Example Usage ---
if __name__ == "__main__":
    TARGET_DOCUMENT_ID = "12RzrqWU-ppj5uoQdY3S7_0KTXhBFnJ0Gzrz7N0kVAoU" # <<< CHANGE THIS TO YOUR DOC ID

    if not all([GOOGLE_REFRESH_TOKEN, GOOGLE_TOKEN_URI, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]):
         print("\n🛑 Cannot run example: Google credentials missing in .env")

    elif TARGET_DOCUMENT_ID == "YOUR_DOCUMENT_ID_HERE": # Add a check for the placeholder
        print("\n⚠️ Please replace 'YOUR_DOCUMENT_ID_HERE' with your actual Google Doc ID in the script.")
    else:
        # Example 1: Add to existing date (Using new keys)
        appt_data_1 = {
            'name': 'API Client Test',
            'date_time': '2025-04-10T14:30', # Make sure this date exists or adjust
            'deposit': '20$', # New key
            'deal_price': '60', # New key
            'service': 'API Refill',
            'notes': 'Via Script' # 'notes' is no longer used in format, but can be kept if needed elsewhere
        }
        print("\n--- Attempting to add appointment 1 (Existing Date) ---")
        add_appointment_to_google_doc(TARGET_DOCUMENT_ID, appt_data_1)


        # Example 2: Add a new date (Using new keys, no service)
        appt_data_2 = {
            'name': 'Future API Booking',
            'date_time': '2025-04-21T10:00', # Choose a date likely not present
            'deposit': '50', # New key
            'deal_price': '120', # New key
            'service': '', # Empty service
            'notes': 'API Deposit Paid'
        }
        print("\n--- Attempting to add appointment 2 (New Date) ---")
        add_appointment_to_google_doc(TARGET_DOCUMENT_ID, appt_data_2)

        # Example 3: Add another appointment (Using new keys)
        appt_data_3 = {
            'name': 'Second Future API',
            'date_time': '2025-04-18T15:00', # Same date as above, later time
            'deposit': '10$', # New key
            'deal_price': '30', # New key
            'service': 'API Touchup',
            'notes': ''
        }
        print("\n--- Attempting to add appointment 3 (To potentially new date) ---")
        add_appointment_to_google_doc(TARGET_DOCUMENT_ID, appt_data_3)
