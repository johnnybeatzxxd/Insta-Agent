import json
import requests
import os 
from dotenv import load_dotenv
import base64
import re
import time
import random

load_dotenv(override=True)

# --- Configuration ---
SHORT_CHUNK_THRESHOLD = 30 # Combine chunks shorter than this length with the next one
# ---------------------

def _preprocess_markdown_links(text):
    """Replaces Markdown links [text](url) with 'text url'."""
    # Regex to find Markdown links: [text](url)
    markdown_link_pattern = r'\[(.*?)\]\((.*?)\)'
    # Replace with "text url"
    processed_text = re.sub(markdown_link_pattern, r'\1 \2', text)
    return processed_text

def _split_message_into_chunks(message_text):
    """Helper function to split text based on sentence terminators or newlines,
    keeping punctuation attached to subsequent emojis, even with spaces."""
    # Preprocess to handle Markdown links first
    processed_text = _preprocess_markdown_links(message_text)

    # Define a more comprehensive emoji character class including multiple Unicode ranges
    EMOJI_CLASS = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E6-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF\U00002600-\U000026FF]'

    # Regex revised to handle spaces between punctuation and emojis, using the broader EMOJI_CLASS.
    # 1. Match URLs: (?:https?://|ftps?://|www\.)[^\s]+
    # 2. OR Match content .+? ending in one of:
    #    a. Punctuation [.!?] followed by (whitespace NOT followed by emoji `\s+(?!{EMOJI_CLASS})`) OR end-of-string `$`.
    #    b. Punctuation [.!?] followed by optional spaces `\s*` and emoji(s) `{EMOJI_CLASS}+`, which are then followed by whitespace `\s+` or end-of-string `$`.
    #    c. A newline (\n).
    #    Uses non-greedy .+? which consumes up to and including the matched ending.
    # 3. Fallback: Match any remaining characters using .+
    pattern = rf'(?:https?://|ftps?://|www\.)[^\s]+|.+?(?:[.!?](?=\s+(?!{EMOJI_CLASS})|$)|[.!?]\s*{EMOJI_CLASS}+(?=\s+|$)|\n)|.+'


    # Find all matches based on the pattern using the processed text
    matches = re.finditer(pattern, processed_text)

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

    # Preprocess markdown links before splitting and combining
    processed_message_text = _preprocess_markdown_links(message_text)

    # Step 1: Split the processed message initially
    initial_chunks = _split_message_into_chunks(processed_message_text)

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

def get_user_conversation(user_id):
    """Fetches the conversation history for a specific user_id."""
    access_token = os.environ.get("long_access_token")
    if not access_token:
        print("Error: Long-lived access token not found in environment variables.")
        return None

    # Use the latest API version you have access to, v22.0 seems current based on your example
    url = f"https://graph.instagram.com/v22.0/me/conversations"
    payload = {
        "platform": "instagram",
        "fields": "participants,message,messages{created_time,from,message,reactions,shares,attachments}", # Fetch necessary fields
        "access_token": access_token,
        "user_id": user_id # Filter by user ID
    }

    print(f"Fetching conversation for user_id: {user_id}")
    try:
        response = requests.get(url, params=payload)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # Debugging: Print the raw API response
        # print("Raw API response for user_id", user_id, ":", json.dumps(data, indent=2))

        # Check if the response contains data and the expected structure
        if data and "data" in data and len(data["data"]) > 0:
            # Since we filter by user_id, we expect at most one conversation thread
            conversation_thread = data["data"][0]
            if "messages" in conversation_thread and "data" in conversation_thread["messages"]:
                messages = conversation_thread["messages"]["data"]
                print(f"Found {len(messages)} messages in API for user_id: {user_id}")
                # API returns messages newest-to-oldest, reverse to get chronological order
                return messages[::-1] # Return messages in chronological order (oldest first)
            else:
                print(f"No 'messages' found in the conversation thread for user_id: {user_id}")
                return [] # Return empty list if no messages field
        else:
            print(f"No conversation data found in API response for user_id: {user_id}")
            return [] # Return empty list if no data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching conversation for user_id {user_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             try:
                 print(f"API Error Response Body: {e.response.json()}")
             except json.JSONDecodeError:
                 print(f"API Error Response Text: {e.response.text}")
        return None # Indicate an error occurred

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

def send_post(receiver_id,post_id,owner_id):

    access_token = os.environ.get("long_access_token")
    url = f"https://graph.instagram.com/v22.0/{owner_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {
            "id": receiver_id
        },
        "message": {
            "attachment": {
                "type": "MEDIA_SHARE",
                "payload": {
                    "id": post_id
                }
            }
        }
    }

    response = requests.post(url,headers=headers,data=json.dumps(data))
    print(response.json())

def send_entrance_image(receiver_id):
    access_token = os.environ.get("long_access_token")
    image_url = "https://media-hosting.imagekit.io/e7ea7d1a0e2f462f/photo_2025-05-06_19-22-43.jpg?Expires=1841310388&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=z8G3NXKZaOS8YC3FSeuOBoRmBqONo-FR9MXVUjlav-j5eMf0MBOQQoMk5uRk3-MiH8sr31ZICz3Qm2hjxmAoH~pGkzMoFLa9r~XcYB8H1h9F2oB-bYLswGtOVjlzEmD2JSdSi~YBZC5dChm5pbuj6dH30fRDJaCJXQrqNSG1AhshZ2eXV1QzVyKSdHL44fluwFBWHZKizJv-BAGZviWhtNodV9-UU~Z~O4Ozh2tjsqOfxn0rwppdRICuIae7MOF~SqFAxhPquJ9AUlxTlAJ2XVVxTnkyJ1zvlsK6QzO~7coP~ycMI76thqK1UEeKX1hje6nFfrz3-Ld0DVRbhA2PTw__"
    url = f"https://graph.instagram.com/v12.0/me/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {
            "id": receiver_id
        },
        "message":{
              "attachment":{
               "type":"image",
               "payload":{
                 "url":image_url,
               }
             }
           }
    }

    response = requests.post(url,headers=headers,data=json.dumps(data))
    print(response.json())


if __name__ == "__main__":
    # --- Test get_user_conversation ---
    # Replace with a valid user_id you want to test with
    test_user_id = "1062589199314901" # Example ID from your request
    print(f"\n--- Testing get_user_conversation for user: {test_user_id} ---")
    conversation_messages = get_user_conversation(test_user_id)
    if conversation_messages is not None:
        print(f"Retrieved {len(conversation_messages)} messages from API.")
        # Optional: Print the messages for verification
        for msg in conversation_messages:
            print(json.dumps(msg, indent=2))
    else:
        print("Failed to retrieve conversation from API.")
    # --- End Test ---
