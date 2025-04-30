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

TARGET_TZ = pytz.timezone('America/New_York')

load_dotenv(override=True)

# owner_id = os.environ.get("owner_id")

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

def process_message_batch(sender_id, owner_id):
    """Process messages for a sender, discarding results if new messages arrived during processing."""
    print(f"Attempting to process batch for {sender_id}")
    
    with processing_locks[sender_id]:
        # Clear the timer reference now that we are processing
        if sender_id in batch_timers:
            print(f"Cleared timer reference for {sender_id}")
            del batch_timers[sender_id] # Remove timer from tracking

        # Prevent re-entrancy if somehow triggered again while processing
        if is_processing[sender_id]:
            print(f"Warning: process_message_batch called for {sender_id} while already processing. Aborting this call.")
            return

        # Mark as processing
        is_processing[sender_id] = True
        
        # Record the timestamp of the latest message we know about *before* starting AI
        start_processing_based_on_ts = last_message_timestamp[sender_id]
        print(f"Starting processing for {sender_id}. Baseline timestamp: {start_processing_based_on_ts}")
        
        # Temporarily release lock for the long AI call
        # This allows process_messages to update last_message_timestamp if new messages arrive
    
    # --- AI Processing (Lock Released) ---
    ai_generated_messages = []
    try:
        if database.check_user_active(sender_id, owner_id) and database.check_bot_active(owner_id):
            latest_conversation = database.get_conversation(sender_id, owner_id)
            if not latest_conversation:
                 print(f"No conversation found for active user {sender_id}. Skipping AI.")
            else:
                print(f"Processing conversation for {sender_id}. Length: {len(latest_conversation)}")
                llm = ai.llm(owner_id)
                ai_generated_messages = llm.process_query(sender_id, latest_conversation, owner_id)
                print(f"AI generated {len(ai_generated_messages)} messages for {sender_id}")
        else:
            print(f"User {sender_id} is not active. Skipping AI processing.")
            
    except Exception as e:
         print(f"Error during AI processing for {sender_id}: {e}")
         # Handle error appropriately, maybe log it
         ai_generated_messages = [] # Ensure it's empty on error
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
                # Process and send the response as no new messages arrived
                if ai_generated_messages:
                     # database.add_message(sender_id, ai_generated_messages, owner_id) # Assuming this happens elsewhere or is handled by process_query returning the messages

                     # --- REVISED LOGIC START ---
                     # Extract all user-facing text content from the AI messages into a list
                     user_facing_content = []
                     for msg in ai_generated_messages:
                         if msg.get("role") == "assistant" and msg.get("content"):
                             # Content is expected to be a list of blocks
                             if isinstance(msg["content"], list):
                                 # Extract text from any 'text' type blocks within the content list
                                 text_parts = [
                                     block.get("text", "") 
                                     for block in msg["content"] 
                                     if isinstance(block, dict) and block.get("type") == "text"
                                 ]
                                 # Join text parts from the *same* assistant message if needed, 
                                 # but add each resulting message's text to the list
                                 combined_text = " ".join(filter(None, text_parts)).strip()
                                 if combined_text:
                                     user_facing_content.append(combined_text)
                             elif isinstance(msg["content"], str):
                                 # Fallback: If content is just a string (less likely with Anthropic tools format)
                                 if msg["content"].strip():
                                     user_facing_content.append(msg["content"].strip())
                             # Note: We are specifically ignoring tool_use and tool_result content here for sending.
                     
                     print(f"Sending user_facing_content list to {sender_id}: {user_facing_content}")
                     if user_facing_content:
                         # Pass the list of strings directly to send_text_messages
                         actions.send_text_messages(sender_id, user_facing_content)
                     else:
                         print(f"No user-facing text content generated by AI for {sender_id}.")
                     # --- REVISED LOGIC END ---
                else:
                     print(f"No AI messages were generated for {sender_id}.")

            else:
                # New message(s) arrived during processing. Discard result and reschedule.
                print(f"New message arrived for {sender_id} during processing. Discarding response and rescheduling.")
                
                # Schedule the next run immediately (or with a tiny delay)
                if sender_id in batch_timers: # Clear any potentially conflicting timer
                    try:
                        batch_timers[sender_id].cancel()
                    except Exception: pass
                    del batch_timers[sender_id]

                # Use a small delay (e.g., 0.1s) instead of 0 to avoid potential stack issues if things happen extremely fast
                print(f"Scheduling immediate reprocessing for {sender_id}")
                batch_timers[sender_id] = threading.Timer(
                    0.1,
                    process_message_batch,
                    args=[sender_id, owner_id]
                )
                batch_timers[sender_id].start()

            # Mark processing as finished for this cycle
            is_processing[sender_id] = False
            print(f"Set is_processing=False for {sender_id}")
            # Lock is released automatically here

def process_messages(request):
    owner_id = request["entry"][0]["id"]
    sender = request["entry"][0]["messaging"][0]["sender"]["id"]
    receiver = request["entry"][0]["messaging"][0]["recipient"]["id"]
    message_obj = request["entry"][0]["messaging"][0]

    if sender == str(owner_id):  # The owner sent a message
        print(f"Message sent to {receiver}")
        msg = message_obj["message"]["text"]
        today = datetime.datetime.now(tz=TARGET_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
        # msg = f"{today}\n{msg}"
        message = {
            "role": "assistant",
            "content": msg
        }
        if message_obj["message"]["is_echo"] != "true":
            print("its not echo")
            database.add_message(receiver, [message], owner_id)
        return

    if receiver == str(owner_id):  # The owner received a message
        print(f"Message received from {sender}")
        
        # Acquire lock specific to this sender
        with processing_locks[sender]:
            # 1. Record the timestamp immediately
            now_ts = datetime.datetime.now(tz=TARGET_TZ)
            last_message_timestamp[sender] = now_ts
            print(f"Updated last_message_timestamp for {sender} to {now_ts}")

            # 2. Prepare and save the message to DB
            message = message_obj["message"]
            user_message = {"role": "user", "content": None}
            msg_content_parts = [] # Build content using parts

            # Handle text
            if "text" in message:
                # Keep original timestamp logic *within* the message content if needed
                # today_str = now_ts.strftime("%Y-%m-%d %H:%M:%S %Z")
                # msg_with_timestamp = f"{today_str}\n{message['text']}"
                # For multi-modal, prefer structured format
                msg_content_parts.append({"type": "text", "text": message['text']})


            # Handle image attachments
            attachments = message.get("attachments", [])
            for attachment in attachments:
                if attachment["type"] == "image":
                    image_url = attachment["payload"]["url"]
                    print(f"Processing image attachment from URL: {image_url}")
                    base64_data, media_type = functions.url_to_base64(image_url) # Get base64 and type

                    if base64_data and media_type:
                        print(f"Successfully converted image to base64. Media Type: {media_type}")
                        msg_content_parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type, # Use detected media type
                                "data": base64_data      # Use base64 data
                            }
                        })
                    else:
                        print(f"Failed to convert image from URL: {image_url}")
                        # Optionally, append a text note indicating failure, or just skip
                        # msg_content_parts.append({"type": "text", "text": "[Image failed to load]"})


            # Assign content based on parts
            # --- MODIFIED LOGIC TO ALWAYS USE LIST FORMAT FOR CONSISTENCY ---
            if msg_content_parts:
                 user_message["content"] = msg_content_parts # Always use list format if there's any content
            else:
                 user_message = None # Don't save if no text or image

            # --- END MODIFIED LOGIC ---


            if user_message and user_message["content"]:
                # print(f"Saving message for {sender}: {json.dumps(user_message, indent=2)}") # Pretty print for inspection
                database.add_message(sender, [user_message], owner_id)
            else:
                 print(f"No content to save for message from {sender}")


            # 3. Manage Batch Timer
            timer_exists = sender in batch_timers and batch_timers[sender].is_alive()
            
            # Only start a new timer if processing is NOT active and no timer is already running
            if not is_processing[sender] and not timer_exists:
                print(f"Starting batch timer for {sender}")
                # Clear any old reference just in case
                if sender in batch_timers:
                    del batch_timers[sender]
                    
                batch_timers[sender] = threading.Timer(
                    BATCH_WINDOW,
                    process_message_batch,
                    args=[sender, owner_id]
                )
                batch_timers[sender].start()
            elif is_processing[sender]:
                 print(f"Processing already active for {sender}, timer not started.")
            elif timer_exists:
                 print(f"Timer already running for {sender}, not starting a new one.")
                 
        # Lock is released automatically here

if __name__ == "__main__":
    database.reset_conversation(1660159627957434)
    print("Database reset done!")

