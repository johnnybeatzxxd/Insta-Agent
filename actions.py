import json
import requests
import os 
from dotenv import load_dotenv

load_dotenv(override=True)

def send_text_message(recipient_id, message_text):
    """
    Sends a text message to a recipient using the Instagram Graph API
    
    Args:
        recipient_id (str): The ID of the recipient
        message_text (str): The text message to send
    """
    access_token = os.environ.get("long_access_token")
    
    # API endpoint for sending messages
    url = "https://graph.instagram.com/v12.0/me/messages"
    
    # Construct message payload
    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    }
    
    # Request headers 
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    print("headers",headers)
    
    # Send POST request
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
        return response
        
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {str(e)}")
        return None
send_text_message(1660159627957434,"hi how are you today!")
