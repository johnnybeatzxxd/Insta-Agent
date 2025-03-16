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

load_dotenv(override=True)

owner_id = os.environ.get("owner_id")

# Message batching system
message_batches = defaultdict(list)
batch_timers = {}
batch_locks = defaultdict(threading.Lock)
BATCH_WINDOW = 5  # seconds to wait for related messages

def process_message_batch(sender_id,owner_id):
    """Process a complete batch of messages from a sender"""
    with batch_locks[sender_id]:
        if sender_id in message_batches:
            # Clear the batch (messages already saved individually)
            message_batches[sender_id] = []
            
            if database.check_user_active(sender_id,owner_id):
                # Get conversation from database
                latest_conversation = database.get_conversation(sender_id,owner_id)
                print("Processing batched conversation:", latest_conversation)
                
                # Process with AI
                llm = ai.llm(owner_id)
                response = llm.generate_response(sender_id, latest_conversation,owner_id)
                actions.send_text_message(sender_id, response)

def process_messages(request):
    owner_id = request["entry"][0]["id"]
    sender = request["entry"][0]["messaging"][0]["sender"]["id"]
    receiver = request["entry"][0]["messaging"][0]["recipient"]["id"]
    message_obj = request["entry"][0]["messaging"][0]

    if sender == str(owner_id):  # The owner sent a message
        print(f"Message sent to {receiver}")
        msg = message_obj["message"]["text"]
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"{today}\n{msg}"
        message = {
                "role": "model",
                "parts": [{"text": msg}]
            }
        database.add_message(receiver, [message], owner_id,"model")
        return
        
    if receiver == str(owner_id):  # The owner received a message
        print(f"Message received from {sender}")
        
        # Add this message to the sender's batch
        with batch_locks[sender]:
            message_batches[sender].append(message_obj)
            
            # Immediately save the message to database
            message = message_obj["message"]
            parts = []
            msg = message["text"]
            today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"{today}\n{msg}"
            # Handle text content
            if "text" in message:
                parts.append({"text": msg})
            
            # Handle image attachments
            attachments = message.get("attachments", [])
            for attachment in attachments:
                if attachment["type"] == "image":
                    parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": actions.image_to_base64(attachment["payload"]["url"])
                        }
                    })
            
            if parts:  # Only save if we have content
                user_message = [{"role": "user", "parts": parts}]
                database.add_message(sender, user_message,owner_id, "user")
            
            # If this is the first message in the batch, start a timer
            if sender in batch_timers and batch_timers[sender].is_alive():
                # Timer already running, don't need to start a new one
                pass
            else:
                # Start a new timer
                batch_timers[sender] = threading.Timer(
                    BATCH_WINDOW, 
                    process_message_batch, 
                    args=[sender,owner_id]
                )
                batch_timers[sender].start()

if __name__ == "__main__":
    database.reset_conversation(1660159627957434)
    print("Database reset done!")

