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
BATCH_WINDOW = 1  # seconds to wait for related messages

def process_message_batch(sender_id,owner_id):
    """Process a complete batch of messages from a sender"""
    with batch_locks[sender_id]:
        if sender_id in message_batches:
            # Clear the batch (messages already saved individually)
            message_batches[sender_id] = []
            
            if database.check_user_active(sender_id,owner_id):
                latest_conversation = database.get_conversation(sender_id,owner_id)
                print("Processing batched conversation:", latest_conversation)
                # Process with AI
                llm = ai.llm(owner_id)
                # process_query now returns all messages added by the AI this turn
                ai_generated_messages = llm.process_query(sender_id,latest_conversation,owner_id)
                print(f"AI generated messages: {ai_generated_messages}")
                
                # Save all AI-generated messages (assistant, tool_calls, tool responses) to DB
                if ai_generated_messages:
                    database.add_message(sender_id, ai_generated_messages, owner_id)
                    print(f"Saved AI generated messages to DB for {sender_id}")

                # Filter out only the user-facing text responses to send back
                user_facing_content = []
                for msg in ai_generated_messages:
                    if msg.get("role") == "assistant" and msg.get("content"):
                        user_facing_content.append(msg["content"])
                
                print(f"Sending user_facing_content: {user_facing_content}")
                # Send the filtered response content to the user
                if user_facing_content:
                    actions.send_text_messages(sender_id, user_facing_content)
                else:
                    # Handle cases where AI might only make tool calls without a final text response
                    print(f"No direct user-facing text content from AI for {sender_id}. Only tool calls/responses occurred.") 
                    # Optionally send a default message like "Okay, processing that." or nothing.

def process_messages(request):
    owner_id = request["entry"][0]["id"]
    sender = request["entry"][0]["messaging"][0]["sender"]["id"]
    receiver = request["entry"][0]["messaging"][0]["recipient"]["id"]
    message_obj = request["entry"][0]["messaging"][0]

    if sender == str(owner_id):  # The owner sent a message
        print(f"Message sent to {receiver}")
        msg = message_obj["message"]["text"]
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        
        # Add this message to the sender's batch
        with batch_locks[sender]:
            message_batches[sender].append(message_obj)
            
            # Immediately save the message to database
            message = message_obj["message"]
            user_message = {"role": "user", "content": None}
            
            # Handle text content
            if "text" in message:
                msg = message["text"]
                today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = f"{today}\n{msg}"
                user_message["content"] = msg
            
            # Handle image attachments
            attachments = message.get("attachments", [])
            if attachments:
                user_message["content"] = []  # Initialize as list for multimodal content
                if user_message["content"] is None:
                    user_message["content"] = []
                
                # Add text if exists
                if "text" in message:
                    user_message["content"].append({
                        "type": "text",
                        "text": msg
                    })
                
                # Add images
                for attachment in attachments:
                    if attachment["type"] == "image":
                        user_message["content"].append({
                            "type": "image_url",
                            "image_url": {
                                "url": attachment["payload"]["url"]
                            }
                        })
            
            if user_message["content"]:  # Only save if we have content
                database.add_message(sender, [user_message], owner_id)
            
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

