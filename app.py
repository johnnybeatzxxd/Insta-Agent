import json
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import os
from dotenv import load_dotenv
from message_manager import process_messages
import threading
import time
import database
import actions
import dashboard

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
cors = CORS(app)
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
                message_id = notification["entry"][0]["time"]
                
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
        
        
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route("/signup",methods=['POST'])
def signup():
    if request.method == "POST":
        creds = request.get_json()
        _id = creds.get("_id")
        email = creds.get("email")
        password = creds.get("password")
        access_token = creds.get("access_token")
        
        create_user = database.auth()
        user = create_user.signup(_id,email,password,access_token)

    return jsonify({'stats':'signed up'}), 200
@app.route('/login',methods=['POST'])
def login():
    if request.method == "POST":
        creds = request.get_json()
        username = creds.get("username")
        password = creds.get("password")
        authenticate = database.auth()
        user = authenticate.login(username=username,password=password)
        
        if user:
            response = {"_id":user["_id"],"username":user["username"],"cookie":user["cookie"]}
            return jsonify({'stats':'logged in','user':response}), 200
        return jsonify({"message":'Invalid credentials!'}), 400

@app.route('/dashboard', methods=['GET'])
def dash():
    if request.method == "GET":
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': "Missing or invalid Authorization header"}), 400
            
        cookie = auth_header.split(' ')[1]  # Extract token after 'Bearer '
        
        authentication = database.auth()
        user = authentication.login(cookie=cookie)
        if user is None:
            return jsonify({'message': "wrong credentials"}), 400

        user_id = user["_id"]
        access_token = user["access_token"]
        
        if user:
            response = dashboard.dashboard_stats(user_id,access_token)
            # print('this is the response:',response)
            return jsonify({'data': response}), 200

        return jsonify({'message': "Access Token Expired!"}), 400

@app.route('/switch', methods=['POST'])
def switch():
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'message': "Missing or invalid Authorization header"}), 400
        
    cookie = auth_header.split(' ')[1] 
    
    authentication = database.auth()
    user = authentication.login(cookie=cookie)
    if user is None:
        return jsonify({'message': "wrong credentials"}), 400
    owner_id = user["_id"]
    body = request.get_json()
    customer_id = body["userId"]
    is_enabled = body["is_enabled"]
    database.set_user_active(customer_id,is_enabled,owner_id)
    
    return jsonify({'message': "updated"}), 200


@app.route('/delete_customer',methods=['POST'])
def cust():
    if request.method == "POST":
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': "Missing or invalid Authorization header"}), 400
            
        cookie = auth_header.split(' ')[1]  # Extract token after 'Bearer '
        
        authentication = database.auth()
        user = authentication.login(cookie=cookie)
        if user is None:
            return jsonify({'message': "wrong credentials"}), 400

        user_id = user["_id"]
        access_token = user["access_token"]
        
        body = request.get_json()
        _id = body.get("_id")
        owner_id = body.get("owner_id") 
        if user:
            database.delete_customer(_id,owner_id) 
            pass
            return jsonify({'message': f"{_id} deleted!"}), 200
        
        return jsonify({'message': "couldnt delete the user"}), 400

@app.route('/business_data',methods=['GET'])
def deta():
    if request.method == "GET":
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': "Missing or invalid Authorization header"}), 400
            
        cookie = auth_header.split(' ')[1]  # Extract token after 'Bearer '
        
        authentication = database.auth()
        user = authentication.login(cookie=cookie)
        if user is None:
            return jsonify({'message': "wrong credentials"}), 400

        owner_id = user["_id"]
        
        business_data = database.get_business_data(owner_id)

        return jsonify({'data': business_data}), 200

@app.route('/save_business_data',methods=['POST'])
def data():
    if request.method == "POST":
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': "Missing or invalid Authorization header"}), 400
            
        cookie = auth_header.split(' ')[1]  # Extract token after 'Bearer '
        
        authentication = database.auth()
        user = authentication.login(cookie=cookie)
        if user is None:
            return jsonify({'message': "wrong credentials"}), 400

        owner_id = user["_id"]
        body = request.get_json()
        business_data = body.get("business_data")
        database.set_dataset(owner_id,business_data)
        return jsonify({'message': "Business data saved!"}), 200

@app.route('/get_notifications',methods=['GET'])
def get_notifications():
    if request.method == "GET":
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': "Missing or invalid Authorization header"}), 400
            
        cookie = auth_header.split(' ')[1]  # Extract token after 'Bearer '
        
        authentication = database.auth()
        print("sending")
        user = authentication.login(cookie=cookie)
        print(user)
        if user is None:
            return jsonify({'message': "wrong credentials"}), 400
        owner_id = user.get("_id")
        notificaitons = database.get_notifications(owner_id)


    
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
