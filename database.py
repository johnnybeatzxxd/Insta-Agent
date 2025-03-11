from pymongo import MongoClient
import os
from dotenv import load_dotenv


load_dotenv(override=True)

MONGO_URL = os.getenv('MONGO_URL')
client = MongoClient(MONGO_URL)
db = client['BeautySalonChats']
Users = db['users']  

instruction = "you are solana crypto trading assistant"

def reset_conversation(_id):
    Users.update_one({"_id":_id},{"$set":{"conversation":[]}})

def register(_id): 
    existance = Users.find_one({"_id":_id})
    if existance == None:
        Users.insert_one({"_id":_id,"conversation":[]})
    
def add_message(_id, messages, role=None):
    """Adds messages to conversation, handling both single and bulk operations."""
    try:
        # Handle legacy single message format
        if not role:
            messages = [{"role": role, "parts": messages}]
        
        Users.update_one(
            {"_id": _id},
            {"$push": {"conversation": {"$each": messages}}},
            upsert=True
        )

        user = Users.find_one({"_id": _id}, {"conversation": 1, "_id": 0})
        return user["conversation"]
    except Exception as e:
        print(f"Error adding messages: {e}")
        return []

def set_user_info(_id,info):
    Users.update_one({"_id":_id},{"$set":info})

def get_conversation(_id):
    user = Users.find_one({"_id": _id})
    return user.get("conversation", []) if user else []

    
