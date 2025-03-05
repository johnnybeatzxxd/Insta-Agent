import json
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from message_manager import process_messages

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)

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
            print(json.dumps(request.get_json(), indent=4))
            notification = request.get_json()
            is_message = notification["entry"][0].get("messaging",None)
            print(is_message)
            if is_message is not None:
                process_messages(notification)
        except Exception as e:
            print("error:",e)
        return "<p>This is POST Request, Hello Webhook!</p>"
    
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
