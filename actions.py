import json
import requests
import os 
from dotenv import load_dotenv
import base64
import database
import re
import time
import random

load_dotenv(override=True)

# --- Configuration ---
SHORT_CHUNK_THRESHOLD = 30 # Combine chunks shorter than this length with the next one
# ---------------------

def _split_message_into_chunks(message_text):
    """Helper function to split text based on sentence terminators (unless followed by emoji) and newlines."""
    # Regex to split messages after sentences/newlines.
    # Splits after '.', '!', '?' ONLY if NOT followed by whitespace + emoji.
    # Also splits after '\n'.
    # Emoji range U+1F300 to U+1FADF covers many common emojis.
    pattern = r'.+?(?:[.!?](?!(?:\s|\u00A0)*[\U0001F300-\U0001FADF])|\n)|.+'

    # Find all matches based on the pattern
    matches = re.finditer(pattern, message_text)

    # Create chunks, stripping leading/trailing whitespace
    message_chunks = [match.group(0).strip() for match in matches]

    # Filter out any potentially empty chunks
    message_chunks = [chunk for chunk in message_chunks if chunk]
    return message_chunks

def _combine_short_chunks(chunks, min_length):
    """Combines consecutive chunks if the first one is shorter than min_length."""
    if not chunks:
        return []

    combined_chunks = []
    i = 0
    while i < len(chunks):
        current_chunk = chunks[i]

        # Check if current chunk is short and there's a next chunk to combine with
        if len(current_chunk) < min_length and (i + 1) < len(chunks):
            # Combine with the next chunk
            combined = current_chunk + " " + chunks[i+1]
            combined_chunks.append(combined.strip()) # Add combined chunk
            i += 2 # Skip the next chunk as it's already combined
        else:
            # Add the current chunk as is
            combined_chunks.append(current_chunk)
            i += 1 # Move to the next chunk

    return combined_chunks

def send_text_message(recipient_id, message_text):
    """
    Sends a text message to a recipient using the Instagram Graph API, splitting the message
    into smaller chunks and combining short chunks for a more natural flow.
    Includes a random delay between sending chunks.

    Args:
        recipient_id (str): The ID of the recipient
        message_text (str): The text message to send
    """
    access_token = os.environ.get("long_access_token")

    # Step 1: Split the message initially
    initial_chunks = _split_message_into_chunks(message_text)

    # Step 2: Combine short chunks
    final_chunks = _combine_short_chunks(initial_chunks, SHORT_CHUNK_THRESHOLD)

    # If no final chunks were created, return
    if not final_chunks:
        print("No valid message chunks to send after combining.")
        return None

    responses = []
    # API endpoint for sending messages
    url = "https://graph.instagram.com/v12.0/me/messages"

    # Request headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Send each final chunk as a separate message
    for chunk in final_chunks:
        # Construct message payload
        payload = {
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": chunk
            }
        }

        # --- Add Delay Before Sending ---
        # Pause for a short, random time to simulate typing
        delay_seconds = random.uniform(0.5, 3.0) # Delay between 0.5 and 1.5 seconds
        print(f"Pausing for {delay_seconds:.2f} seconds...")
        time.sleep(delay_seconds)
        # --------------------------------

        # Send POST request
        print(f"Sending chunk: {chunk}")
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload
            )

            # Log response details
            print(f"Response Status Code: {response.status_code}")

            try:
                print(f"Response Body: {response.json()}")
            except requests.exceptions.JSONDecodeError:
                print(f"Failed to decode JSON response. Raw response: {response.text}")

            # Check if request was successful
            response.raise_for_status()
            responses.append(response)

        except requests.exceptions.RequestException as e:
            print(f"Error sending message chunk: {str(e)}")

    return responses if responses else None

def image_to_base64(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    else:
        return None
    
def send_text_messages(recipient_id, messages):
    # for message in messages:
    send_text_message(recipient_id,messages[-1])


def get_conversations(access_token):

    # access_token = os.environ.get("long_access_token")
    url = f"https://graph.instagram.com/v22.0/me/conversations"
    payload = {
        "platform": "instagram",
        "fields":  "participants,message,messages{created_time,from,message,reactions,shares,attachments}",
        "access_token": access_token
        }
    response = requests.get(url, params=payload)
    if response.status_code == 200:
        data = response.json()
        return data
    return None

def get_profile(_id):
    access_token = os.environ.get("long_access_token")
    url = f"https://graph.instagram.com/v22.0/{_id}"
    payload = {
        "fields": "name,username",
        "access_token": access_token
        }
    response = requests.get(url, params=payload)
    if response.status_code == 200:
        data = response.json()
        return data


if __name__ == "__main__":
    # Example usage for testing the splitting and combining
    test_message = "Ok. Thanks! We have availability tomorrow, Friday! What time works best for you? Let me know. 🥰"
    # test_message = "hey! lash extensions are currently $90 for any set (classic, hybrid, 2-3D, or 4-6D). what day are you thinking of coming in? 🥰"


    print(f"Original Message:\n{test_message}\n")
    print("Processing message...")

    # Step 1: Initial Split
    initial_chunks = _split_message_into_chunks(test_message)

    print("\nResulting Chunks (Initial Split):")
    if initial_chunks:
        for i, chunk in enumerate(initial_chunks):
            print(f"  Chunk {i+1} (len={len(chunk)}): {chunk}")
    else:
        print("  No initial chunks generated.")

    # Step 2: Combine Short Chunks
    final_chunks = _combine_short_chunks(initial_chunks, SHORT_CHUNK_THRESHOLD)

    print(f"\nResulting Chunks (After Combining Short Ones < {SHORT_CHUNK_THRESHOLD} chars):")
    if final_chunks:
        for i, chunk in enumerate(final_chunks):
            print(f"  Final Chunk {i+1}: {chunk}")
    else:
        print("  No final chunks generated.")

    # --- Optional: Simulate Sending ---
    # print("\n--- Simulating Sending ---")
    # if final_chunks:
    #     for i, chunk in enumerate(final_chunks):
    #         delay_seconds = random.uniform(0.5, 1.5)
    #         print(f"Pausing for {delay_seconds:.2f} seconds...")
    #         # time.sleep(delay_seconds) # Uncomment to actually pause
    #         print(f"Sending final chunk {i+1}: {chunk}")
    # else:
    #     print("No chunks to send.")
    # ----------------------------------

