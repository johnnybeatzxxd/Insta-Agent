from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json

from pymongo.synchronous import database
import actions

load_dotenv(override=True)

MONGO_URL = os.getenv('MONGO_URL')
client = MongoClient(MONGO_URL)
db = client['BeautySalonChats']
Users = db['users']
Data = db['data']
creds = db['creds']
appointments = db['appointments']


def reset_conversation(_id,owner_id):
    Users.update_one({"_id":_id,"owner_id":owner_id},{"$set":{"conversation":[]}})

def check_user_active(_id,owner_id):
    user = Users.find_one({"_id":_id,"owner_id":owner_id})
    return user.get("active", True)

def set_user_active(_id,enabled,owner_id):
    Users.update_one({"_id":_id},{"$set":{"active":enabled}})

def add_message(_id, messages,owner_id, role=None):
    """Adds messages to conversation, handling both single and bulk operations."""
    try:
        # Handle legacy single message format
        if not role:
            messages = [{"role": role, "parts": messages}]
        
        Users.update_one(
            {"_id": _id},
            {
                "$push": {"conversation": {"$each": messages}},
                "$setOnInsert": {"active": True,"owner_id":owner_id}
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

def get_conversation(_id,owner_id):
    user = Users.find_one({"_id": _id,"owner_id":owner_id})
    return user.get("conversation", []) if user else []

def set_dataset(_id,dataset):
    Data.update_one(
        {"_id":int(_id)}, 
        {"$set": {"dataset": dataset}},
        upsert=True
    )

def set_instruction(_id,instruction):
    Data.update_one(
        {"_id":_id}, 
        {"$set": {"instruction": instruction}},
        upsert=True
    )

def set_appointment(_id,appointment,owner_id):
    appointments.update_one(
            {"_id":owner_id},
            {"$set":{"appointments":appointment}},
            upsert=True
            )

def get_dataset(owner_id):
    dataset_entry = Data.find_one({"_id":int(owner_id)})
    return dataset_entry.get("dataset") if dataset_entry else None

def get_instruction(owner_id):
    instruction_entry = Data.find_one({"_id":int(owner_id)}, {"instruction": 1, "_id": 0})
    return instruction_entry.get("instruction") if instruction_entry else None

def get_active_users(owner_id):
    active_users = Users.find({"active":True,"owner_id":owner_id})
    return active_users
def get_users(owner_id):
    users = Users.find({"owner_id":owner_id})
    if users is None:
        users = []
    return users 
def delete_customer(_id,owner_id):
    Users.delete_one({"_id":_id,"owner_id":owner_id})

def get_business_data(_id):
    data = Data.find_one({"_id":int(_id)})
    dataset = data["dataset"]
    return dataset

    
class auth:

    def login(self,cookie=None,username=None,password=None):
        if username is None and cookie is not None:
            user = creds.find_one({"cookie":cookie})
        else:
            user = creds.find_one({"username":username,"password":password})
            
        if user is None:
            return None

        return user

    def signup(self,_id,username,password,access_token):
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        cookie = ''.join(secrets.choice(alphabet) for i in range(64))
        creds.insert_one(
            {
                "_id":_id,
                "username":username,
                "password":password,
                "access_token":access_token,
                "cookie":cookie
             }) 

if __name__ == "__main__":
    with open("info.json","r") as info:
        info = json.load(info)
    print("saving!")
    set_dataset(17841433182941465,info)
    print("saved!")
