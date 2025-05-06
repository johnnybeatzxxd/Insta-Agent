import json
import os
from dotenv import load_dotenv
from actions import send_text_message
import actions
import database
import ai
import time
import random
from collections import defaultdict
import threading
import datetime
import pytz
import functions
import traceback # Import traceback for detailed error logging

TARGET_TZ = pytz.timezone('America/New_York')

load_dotenv(override=True)

# owner_id = os.environ.get("owner_id")
access_token = os.environ.get("long_access_token")

# --- New State Variables ---
# Lock for each sender's state
processing_locks = defaultdict(threading.Lock)
# Flag indicating if process_message_batch is running for a sender
is_processing = defaultdict(bool)
# Timestamp of the last message received from a sender
last_message_timestamp = defaultdict(lambda: None)
# Active batch timers
batch_timers = {}
BATCH_WINDOW = 10
# --- End New State Variables ---

# --- Helper Function for Formatting API Messages ---
def _format_api_message(api_msg, sender_id, owner_id):
    """Formats a single message from the Instagram API response into the DB structure."""
    role = "unknown"
    sender_info = api_msg.get('from', {})
    message_sender_id = sender_info.get('id')

    # Ensure owner_id is string for comparison if needed
    owner_id_str = str(owner_id)

    if message_sender_id == sender_id:
        role = "user"
    elif message_sender_id == owner_id_str:
        role = "assistant"
    else:
        print(f"Warning: Could not determine role for API message sender {message_sender_id}. Message: {api_msg}")
        return None

    content_parts = []
    text_content = api_msg.get('message')
    if text_content and text_content.strip():
        content_parts.append({"type": "text", "text": text_content.strip()})

    attachments_data = api_msg.get('attachments', {}).get('data', [])
    for attachment in attachments_data:
        image_data = attachment.get("image_data")
        if image_data and image_data.get("url"):
            image_url = image_data["url"]
            print(f"Processing image attachment from API history URL: {image_url}")
            try:
                base64_data, media_type = functions.url_to_base64(image_url)
                if base64_data and media_type:
                    print(f"Successfully converted API image to base64. Media Type: {media_type}")
                    content_parts.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": base64_data}
                    })
                else:
                    print(f"Failed to convert API image from URL: {image_url}")
            except Exception as e:
                print(f"Error converting API image URL {image_url} to base64: {e}")
        # TODO: Handle other attachment types

    if content_parts and role != "unknown":
        return {"role": role, "content": content_parts}
    elif not text_content and not attachments_data:
        print(f"Skipping empty API message: {api_msg}")
        return None
    else:
        print(f"Skipping formatting API message due to no valid content parts or unknown role: {api_msg}")
        return None
# --- End Helper Function ---

def process_message_batch(sender_id, owner_id):
    """Process messages for a sender, syncing short history first, then checking active status."""
    print(f"Attempting to process batch for {sender_id}")

    with processing_locks[sender_id]:
        if sender_id in batch_timers:
            print(f"Cleared timer reference for {sender_id}")
            del batch_timers[sender_id]
        if is_processing[sender_id]:
            print(f"Warning: process_message_batch called for {sender_id} while already processing. Aborting this call.")
            return
        is_processing[sender_id] = True
        start_processing_based_on_ts = last_message_timestamp[sender_id]
        print(f"Starting processing for {sender_id}. Baseline timestamp: {start_processing_based_on_ts}")

    # --- Get DB History and Potentially Sync (BEFORE active check) ---
    ai_generated_messages = []
    final_conversation_history = [] # This will hold the history to be used by AI if active

    try:
        # Ensure owner_id is treated as string
        owner_id_str = str(owner_id)

        # 1. Get current DB state
        latest_conversation_db = database.get_conversation(sender_id, owner_id_str)
        if not latest_conversation_db:
             print(f"No conversation found in DB for user {sender_id}.")
             latest_conversation_db = []

        final_conversation_history = latest_conversation_db # Default to DB state

        # 2. Sync Check: Only run if DB conversation is short
        if len(latest_conversation_db) < 4:
            print(f"DB conversation for {sender_id} is short ({len(latest_conversation_db)} messages). Checking API for potential sync.")
            api_conversation_messages = actions.get_user_conversation(sender_id)

            if api_conversation_messages is not None:
                print(f"Retrieved {len(api_conversation_messages)} messages from API for {sender_id}.")

                # Compare API length with DB length
                if len(api_conversation_messages) > len(latest_conversation_db):
                    print(f"API conversation is longer ({len(api_conversation_messages)}) than DB ({len(latest_conversation_db)}). Formatting and syncing.")

                    # Format API Messages
                    formatted_api_messages = []
                    for api_msg in api_conversation_messages:
                        formatted_msg = _format_api_message(api_msg, sender_id, owner_id_str)
                        if formatted_msg:
                            formatted_api_messages.append(formatted_msg)
                    print(f"Formatted {len(formatted_api_messages)} valid messages from API.")

                    if formatted_api_messages:
                        # Update Database
                        print(f"Attempting to overwrite DB conversation for {sender_id} with {len(formatted_api_messages)} formatted messages.")
                        sync_success = database.set_conversation(sender_id, owner_id_str, formatted_api_messages)

                        if sync_success:
                            print(f"Successfully synced conversation to DB for {sender_id}.")
                            # Update the variable holding the history to use
                            final_conversation_history = formatted_api_messages
                        else:
                            print(f"Failed to sync conversation to DB for {sender_id}. Will use existing DB version if bot is active.")
                            # final_conversation_history remains latest_conversation_db
                    else:
                        print(f"No valid messages after formatting API response for {sender_id}. Will use existing DB version if bot is active.")
                        # final_conversation_history remains latest_conversation_db
                else:
                     print(f"API conversation length ({len(api_conversation_messages)}) not greater than DB length ({len(latest_conversation_db)}). No sync needed.")
                     # final_conversation_history remains latest_conversation_db
            else:
                print(f"Failed to retrieve conversation from API for {sender_id}. Will use existing DB version if bot is active.")
                # final_conversation_history remains latest_conversation_db
        else:
            # DB length is >= 4, skipping API check and sync
            print(f"DB conversation length ({len(latest_conversation_db)}) is >= 4. Skipping API check/sync.")
            # final_conversation_history remains latest_conversation_db

        # --- Now check active status and process AI if applicable ---
        if database.check_user_active(sender_id, owner_id_str) and database.check_bot_active(owner_id_str):
            print(f"User {sender_id} and Bot {owner_id_str} are active.")
            # Proceed with AI processing using the determined (potentially synced) history
            if final_conversation_history:
                print(f"Processing conversation for {sender_id}. Final length used: {len(final_conversation_history)}")
                llm = ai.llm(owner_id_str)
                ai_generated_messages = llm.process_query(sender_id, final_conversation_history, owner_id_str)
                print(f"AI generated {len(ai_generated_messages)} messages for {sender_id}")
            else:
                 # This case should be rare now, only if DB was empty and sync failed/yielded nothing
                 print(f"No conversation history available to process for active user {sender_id}. Skipping AI.")
        else:
            # User or Bot is not active, skip AI processing
            print(f"User {sender_id} or Bot ({owner_id_str}) is not active. Skipping AI processing.")

    except Exception as e:
         print(f"Error during processing/syncing for {sender_id}: {e}\n{traceback.format_exc()}")
         ai_generated_messages = [] # Ensure empty on error
    finally:
        # --- Re-acquire Lock and Check Timestamps ---
        with processing_locks[sender_id]:
            current_last_message_ts = last_message_timestamp[sender_id]
            print(f"Finished processing for {sender_id}. Current last message timestamp: {current_last_message_ts}")

            should_reschedule = (
                current_last_message_ts is not None and
                start_processing_based_on_ts is not None and
                current_last_message_ts > start_processing_based_on_ts
            )

            if not should_reschedule:
                print(f"No new messages arrived for {sender_id} during processing. Proceeding to send.")
                # Process and send the response only if AI was called and generated messages
                if ai_generated_messages:
                     # --- REVISED LOGIC START ---
                     user_facing_content = []
                     for msg in ai_generated_messages:
                         if msg.get("role") == "assistant" and msg.get("content"):
                             if isinstance(msg["content"], list):
                                 text_parts = [
                                     block.get("text", "")
                                     for block in msg["content"]
                                     if isinstance(block, dict) and block.get("type") == "text"
                                 ]
                                 combined_text = " ".join(filter(None, text_parts)).strip()
                                 if combined_text:
                                     user_facing_content.append(combined_text)
                             elif isinstance(msg["content"], str):
                                 if msg["content"].strip():
                                     user_facing_content.append(msg["content"].strip())

                     print(f"Sending user_facing_content list to {sender_id}: {user_facing_content}")
                     if user_facing_content:
                         actions.send_text_messages(sender_id, user_facing_content)
                     else:
                         print(f"No user-facing text content generated by AI for {sender_id}.")
                     # --- REVISED LOGIC END ---
                else:
                     # This case now covers:
                     # 1. AI processing skipped (user/bot inactive)
                     # 2. AI ran but generated no messages
                     # 3. An error occurred before/during AI call
                     print(f"No AI messages were generated or AI was skipped for {sender_id}.")

            else:
                # New message(s) arrived during processing. Discard result and reschedule.
                print(f"New message arrived for {sender_id} during processing. Discarding response and rescheduling.")
                if sender_id in batch_timers: # Clear any potentially conflicting timer
                    try: batch_timers[sender_id].cancel()
                    except Exception: pass
                    del batch_timers[sender_id]

                print(f"Scheduling immediate reprocessing for {sender_id}")
                batch_timers[sender_id] = threading.Timer(
                    0.1, process_message_batch, args=[sender_id, owner_id]
                )
                batch_timers[sender_id].start()

            # Mark processing as finished for this cycle
            is_processing[sender_id] = False
            print(f"Set is_processing=False for {sender_id}")
            # Lock is released automatically here

def process_messages(request):
    # Ensure owner_id is consistently treated (e.g., as string)
    owner_id = request["entry"][0]["id"] # This is usually the Page ID / Bot Owner ID
    messaging_event = request["entry"][0]["messaging"][0]
    sender = messaging_event["sender"]["id"] # This is the User's ID
    receiver = messaging_event["recipient"]["id"] # This is usually the Page ID / Bot Owner ID

    # Check if the recipient ID matches the owner ID
    if receiver != owner_id:
        print(f"Warning: Received message where recipient ({receiver}) doesn't match owner ({owner_id}). Skipping.")
        return

    message_obj = messaging_event # Use the whole messaging event

    # Message SENT BY Owner/Page (treat as 'assistant' message for the other user)
    if sender == owner_id:
        recipient_user_id = message_obj.get("recipient", {}).get("id") # The actual user receiving the message
        if not recipient_user_id:
             print("Error: Owner sent message but recipient ID not found in payload.")
             return

        print(f"Message sent by owner ({owner_id}) to {recipient_user_id}")
        message_content = message_obj.get("message", {})
        msg_text = message_content.get("text")

        if not msg_text:
            print("Owner sent message with no text content. Skipping save.")
            # Handle attachments sent by owner? Currently ignored.
            return

        # Format as assistant message for the *recipient's* conversation history
        message_to_save = {
            "role": "assistant",
            "content": [{"type": "text", "text": msg_text}]
        }

        # Check if it's an echo of the bot's own outgoing message
        # Note: The exact structure/field for "is_echo" needs verification from Meta docs/testing
        is_echo = message_content.get("is_echo", False) # Assume boolean false if missing

        if not is_echo:
            print("Owner message is not an echo, saving to recipient's DB.")
            # Save to the conversation history associated with the *recipient_user_id*
            database.add_message(recipient_user_id, [message_to_save], owner_id)
        else:
            print("Owner message is an echo, not saving.")
        return

    # Message RECEIVED BY Owner/Page (treat as 'user' message from the sender)
    if sender != owner_id: # Redundant check given the logic flow, but explicit
        print(f"Message received by owner ({owner_id}) from user {sender}")

        # Acquire lock specific to this sender
        with processing_locks[sender]:
            # 1. Record the timestamp immediately
            now_ts = datetime.datetime.now(tz=TARGET_TZ)
            last_message_timestamp[sender] = now_ts
            print(f"Updated last_message_timestamp for {sender} to {now_ts}")

            # 2. Prepare and save the message to DB
            message = message_obj.get("message") # Use .get for safety
            if not message:
                print(f"Received message object structure doesn't contain 'message' field for {sender}. Payload: {message_obj}")
                return # Skip processing if no message content

            # Ignore messages potentially marked as echoes from the user side? Unlikely but possible.
            if message.get("is_echo", False):
                print(f"Received echo message from user {sender}. Skipping save/processing.")
                return

            user_message = {"role": "user", "content": None}
            msg_content_parts = [] # Build content using parts

            # Handle text
            text_content = message.get("text")
            if text_content and text_content.strip():
                msg_content_parts.append({"type": "text", "text": text_content.strip()})

            # Handle image attachments
            attachments = message.get("attachments", [])
            for attachment in attachments:
                if attachment.get("type") == "image":
                    image_url = attachment.get("payload", {}).get("url")
                    if image_url:
                        print(f"Processing incoming image attachment from URL: {image_url}")
                        try:
                            base64_data, media_type = functions.url_to_base64(image_url)
                            if base64_data and media_type:
                                print(f"Successfully converted incoming image to base64. Media Type: {media_type}")
                                msg_content_parts.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": base64_data
                                    }
                                })
                            else:
                                print(f"Failed to convert incoming image from URL: {image_url}")
                        except Exception as e:
                             print(f"Error converting incoming image URL {image_url} to base64: {e}")
                    else:
                         print("Incoming image attachment found but no URL in payload.")
                # Handle other incoming attachments if needed (e.g., shares, audio, video)

            # Assign content only if parts were added
            if msg_content_parts:
                 user_message["content"] = msg_content_parts
            else:
                 user_message = None # Don't save if no text or valid image

            # Save the user message to DB if valid
            if user_message:
                print(f"Saving message for user {sender}")
                database.add_message(sender, [user_message], owner_id)
            else:
                 print(f"No content (text/image) to save for message from {sender}")


            # 3. Manage Batch Timer
            timer_exists = sender in batch_timers and batch_timers[sender].is_alive()

            # Only start a new timer if processing is NOT active and no timer is already running
            if not is_processing[sender] and not timer_exists:
                print(f"Starting batch timer for {sender}")
                if sender in batch_timers: # Clear old timer ref just in case
                    try: batch_timers[sender].cancel()
                    except Exception: pass
                    del batch_timers[sender]

                batch_timers[sender] = threading.Timer(
                    BATCH_WINDOW,
                    process_message_batch,
                    # Pass the correct sender ID (user) and owner ID (bot)
                    args=[sender, owner_id]
                )
                batch_timers[sender].start()
            elif is_processing[sender]:
                 print(f"Processing already active for {sender}, timer not started.")
            elif timer_exists:
                 print(f"Timer already running for {sender}, not starting a new one.")

        # Lock is released automatically here

if __name__ == "__main__":
    # Example usage (replace with actual IDs/testing logic if needed)
    # test_sender_id = "USER_PSID" # Replace with a test user PSID
    # test_owner_id = "PAGE_ID"   # Replace with your Page ID
    # print(f"Resetting conversation for sender {test_sender_id}...")
    # database.reset_conversation(test_sender_id, test_owner_id)
    # print("Database reset done!")

    # Example: Manually trigger a batch process for testing the sync
    # print(f"\nManually triggering batch process for {test_sender_id}")
    # process_message_batch(test_sender_id, test_owner_id)

    pass # Keep minimal __main__ or add specific tests

