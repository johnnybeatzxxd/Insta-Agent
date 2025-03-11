import json
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from message_manager import process_messages
import threading
import time

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)

# Add at the top of app.py
processed_message_ids = {}
MESSAGE_EXPIRY = 60  # seconds to remember processed messages

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/privacy_policy")
def privacy_policy():
    with open("./privacy_policy.html", "rb") as file:
        privacy_policy_html = file.read()
    return privacy_policy_html

@app.route("/webhook", methods = ["GET", "POST"])
def webhook():
    if request.method == "POST":
        try:
            notification = request.get_json()
            print(json.dumps(notification, indent=4))
            
            # Check if this is a messaging notification
            is_message = notification["entry"][0].get("messaging", None)
            if is_message is not None:
                # Extract message ID for deduplication
                message_id = notification["entry"][0]["messaging"][0]["message"].get("text")
                
                # Check if we've already processed this message
                current_time = time.time()
                if message_id in processed_message_ids:
                    print(f"Skipping duplicate message: {message_id}")
                    return "OK", 200
                
                # Mark this message as processed
                processed_message_ids[message_id] = current_time
                
                # Clean up old message IDs
                for mid in list(processed_message_ids.keys()):
                    if current_time - processed_message_ids[mid] > MESSAGE_EXPIRY:
                        del processed_message_ids[mid]
                
                # Process the message
                thread = threading.Thread(target=process_messages, args=(notification,))
                thread.start()
            
        except Exception as e:
            print("Error:", e)
        
        return "OK", 200
    
    if request.method == "GET":
        hub_mode = request.args.get("hub.mode")
        hub_challenge = request.args.get("hub.challenge")
        hub_verify_token = request.args.get("hub.verify_token")
        if hub_challenge:
            return hub_challenge
        else:
            return "<p>This is GET Request, Hello Webhook!</p>"

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
