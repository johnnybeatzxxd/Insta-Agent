import json
import requests
import os 
from dotenv import load_dotenv
import base64
import database

load_dotenv(override=True)

def send_text_message(recipient_id, message_text):
    """
    Sends a text message to a recipient using the Instagram Graph API
    
    Args:
        recipient_id (str): The ID of the recipient
        message_text (str): The text message to send
    """
    access_token = os.environ.get("long_access_token")
    
    # Maximum message length allowed by Instagram
    MAX_MESSAGE_LENGTH = 1000
    
    # Split the message into natural chunks
    message_chunks = []
    
    # First try to split by paragraphs
    paragraphs = message_text.split('\n')
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit
        if len(current_chunk + paragraph + '\n') > MAX_MESSAGE_LENGTH:
            # If the paragraph itself is too long, split by sentences
            if len(paragraph) > MAX_MESSAGE_LENGTH:
                sentences = split_into_sentences(paragraph)
                for sentence in sentences:
                    # If the sentence is still too long, split by character
                    if len(sentence) > MAX_MESSAGE_LENGTH:
                        for i in range(0, len(sentence), MAX_MESSAGE_LENGTH):
                            if current_chunk and len(current_chunk) + len(sentence[i:i+MAX_MESSAGE_LENGTH]) > MAX_MESSAGE_LENGTH:
                                message_chunks.append(current_chunk.strip())
                                current_chunk = ""
                            current_chunk += sentence[i:i+MAX_MESSAGE_LENGTH]
                            if len(current_chunk) >= MAX_MESSAGE_LENGTH:
                                message_chunks.append(current_chunk.strip())
                                current_chunk = ""
                    else:
                        if current_chunk and len(current_chunk) + len(sentence) > MAX_MESSAGE_LENGTH:
                            message_chunks.append(current_chunk.strip())
                            current_chunk = ""
                        current_chunk += sentence
                        if len(current_chunk) >= MAX_MESSAGE_LENGTH:
                            message_chunks.append(current_chunk.strip())
                            current_chunk = ""
            else:
                # Add the current chunk to our list of chunks
                if current_chunk:
                    message_chunks.append(current_chunk.strip())
                current_chunk = paragraph + '\n'
        else:
            current_chunk += paragraph + '\n'
    
    # Don't forget the last chunk
    if current_chunk:
        message_chunks.append(current_chunk.strip())
    
    # If no chunks were created (empty message), return
    if not message_chunks:
        return None
    
    responses = []
    # API endpoint for sending messages
    url = "https://graph.instagram.com/v12.0/me/messages"
    
    # Request headers 
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    
    # Send each chunk as a separate message
    for chunk in message_chunks:
        # Construct message payload
        payload = {
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": chunk
            }
        }
        
        # Send POST request
        print(chunk)
        continue
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

def split_into_sentences(text):
    """
    Split text into sentences using common sentence terminators.
    
    Args:
        text (str): The text to split
        
    Returns:
        list: List of sentences
    """
    # Define sentence terminators
    terminators = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
    sentences = []
    
    # Start with the full text
    remaining_text = text
    
    while remaining_text:
        # Find the earliest terminator
        terminator_positions = [(remaining_text.find(term), term) for term in terminators if remaining_text.find(term) != -1]
        
        if terminator_positions:
            # Get the earliest terminator
            pos, term = min(terminator_positions, key=lambda x: x[0])
            # Extract the sentence including the terminator
            sentence = remaining_text[:pos + len(term)]
            sentences.append(sentence)
            # Update remaining text
            remaining_text = remaining_text[pos + len(term):]
        else:
            # No terminator found, treat the rest as a sentence
            sentences.append(remaining_text)
            break
    
    return sentences

def image_to_base64(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    else:
        return None

def get_conversations():

    access_token = os.environ.get("long_access_token")
    url = f"https://graph.instagram.com/v22.0/me/conversations"
    payload = {
        "platform": "instagram",
        "fields":  "participants,message,messages{created_time,from,message,reactions,shares,attachments}",
        "access_token": access_token
        }
    response = requests.get(url, params=payload)
    data = response.json()
    print(json.dumps(data, indent=4))

if __name__ == "__main__":
    database.reset_conversation("1660159627957434")
    print("database gone!")
    # get_conversations()

