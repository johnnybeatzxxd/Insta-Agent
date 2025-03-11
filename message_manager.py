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

load_dotenv(override=True)

owner_id = os.environ.get("owner_id")

# Message batching system
message_batches = defaultdict(list)
batch_timers = {}
batch_locks = defaultdict(threading.Lock)
BATCH_WINDOW = 10  # seconds to wait for related messages

def process_message_batch(sender_id):
    """Process a complete batch of messages from a sender"""
    with batch_locks[sender_id]:
        if sender_id in message_batches and message_batches[sender_id]:
            # Combine all messages in the batch
            combined_messages = []
            
            # First add all text messages
            for message_obj in message_batches[sender_id]:
                message = message_obj["message"]
                # Check if it has text
                if "text" in message:
                    combined_messages.append({"role":"user","parts":[{"text": message["text"]}]})
            
            # Then add all images
            for message_obj in message_batches[sender_id]:
                message = message_obj["message"]
                attachments = message.get("attachments", None)
                if attachments:
                    for attachment in attachments:
                        if attachment["type"] == "image":
                            image_url = attachment["payload"]["url"]
                            last_message =  combined_messages[:1]["parts"]

                            last_message.append({
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": actions.image_to_base64(image_url)
                                }
                            })
            
            # Clear the batch
            message_batches[sender_id] = []
            
            # Only proceed if we have content
            if combined_messages:
                # Add the combined message to the conversation
                database.add_message(sender_id, combined_messages, "user")
                
                # Process with AI
                llm = ai.llm()
                latest_conversation = database.get_conversation(sender_id)
                print("Processing combined batch conversation:", latest_conversation)
                response = llm.generate_response(sender_id, latest_conversation)
                
                # Save and send the response
                actions.send_text_message(sender_id, response)

def process_messages(request):
    owner_id = request["entry"][0]["id"]
    sender = request["entry"][0]["messaging"][0]["sender"]["id"]
    receiver = request["entry"][0]["messaging"][0]["recipient"]["id"]
    message_obj = request["entry"][0]["messaging"][0]

    if sender == str(owner_id):  # The owner sent a message
        print(f"Message sent to {receiver}")
        return
        
    if receiver == str(owner_id):  # The owner received a message
        print(f"Message received from {sender}")
        
        # Add this message to the sender's batch
        with batch_locks[sender]:
            message_batches[sender].append(message_obj)
            
            # If this is the first message in the batch, start a timer
            if sender in batch_timers and batch_timers[sender].is_alive():
                # Timer already running, don't need to start a new one
                pass
            else:
                # Start a new timer
                batch_timers[sender] = threading.Timer(
                    BATCH_WINDOW, 
                    process_message_batch, 
                    args=[sender]
                )
                batch_timers[sender].start()

if __name__ == "__main__":
    database.reset_conversation(1660159627957434)
    print("Database reset done!")

