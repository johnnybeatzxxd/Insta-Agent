from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json

load_dotenv(override=True)

MONGO_URL = os.getenv('MONGO_URL')
client = MongoClient(MONGO_URL)
db = client['BeautySalonChats']
Users = db['users']
Data = db['data']


def reset_conversation(_id):
    Users.update_one({"_id":_id},{"$set":{"conversation":[]}})
def check_user_active(_id):
    user = Users.find_one({"_id":_id})
    return user.get("active", True)
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
            {
                "$push": {"conversation": {"$each": messages}},
                "$setOnInsert": {"active": True}
            },
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
def set_dataset(dataset):
    Data.update_one(
        {}, 
        {"$set": {"dataset": dataset}},
        upsert=True
    )

def set_instruction(instruction):
    Data.update_one(
        {}, 
        {"$set": {"instruction": instruction}},
        upsert=True
    )

def get_dataset():
    dataset_entry = Data.find_one({}, {"dataset": 1, "_id": 0})
    return dataset_entry.get("dataset") if dataset_entry else None

def get_instruction():
    instruction_entry = Data.find_one({}, {"instruction": 1, "_id": 0})
    return instruction_entry.get("instruction") if instruction_entry else None

if __name__ == "__main__":
    pass
