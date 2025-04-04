from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json
from pymongo.synchronous import database
import actions
from bson import ObjectId
from datetime import datetime

load_dotenv(override=True)

MONGO_URL = os.getenv('MONGO_URL')
client = MongoClient(MONGO_URL)
db = client['BeautySalonChats']
Users = db['users']
Data = db['data']
creds = db['creds']
appointments = db['appointments']
notifications = db['notifications']


def reset_conversation(_id,owner_id):
    Users.update_one({"_id":_id,"owner_id":owner_id},{"$set":{"conversation":[]}})

def check_user_active(_id,owner_id):
    user = Users.find_one({"_id":_id,"owner_id":owner_id})
    return user.get("active", True)

def set_user_active(_id,enabled,owner_id):
    Users.update_one({"_id":_id},{"$set":{"active":enabled}})

def add_message(_id, messages, owner_id):
    """Adds messages to the conversation history for a user."""
    try:
        # Ensure messages is always a list
        if not isinstance(messages, list):
            # This case should ideally not happen if called correctly,
            # but provides a fallback just in case.
            # Consider logging a warning here if it occurs.
            print(f"Warning: add_message called with non-list messages for user {_id}. Converting.")
            # Attempt to create a generic structure; adjust if needed based on expected input
            messages = [{"role": "unknown", "content": str(messages)}]

        if not messages:
            print(f"Warning: add_message called with empty message list for user {_id}.")
            return get_conversation(_id, owner_id) # Return current conversation

        Users.update_one(
            {"_id": _id, "owner_id": owner_id}, # Ensure we match owner_id too
            {
                "$push": {"conversation": {"$each": messages}},
                "$setOnInsert": {"active": True, "owner_id": owner_id} # owner_id was missing here
            },
            upsert=True
        )
        # Return the updated conversation after adding messages
        return get_conversation(_id, owner_id)
    except Exception as e:
        print(f"Error adding messages for user {_id}: {e}")
        # Return existing conversation or empty list on error
        return get_conversation(_id, owner_id)

def set_user_info(_id,info):
    Users.update_one({"_id":_id},{"$set":info})

def get_conversation(_id,owner_id):
    user = Users.find_one({"_id": _id,"owner_id":owner_id})
    return user.get("conversation", []) if user else []

def set_dataset(_id,dataset):
    Data.update_one(
        {"_id":_id}, 
        {"$set": {"dataset": dataset}},
        upsert=True
    )

def set_instruction(_id,instruction):
    Data.update_one(
        {"_id":_id}, 
        {"$set": {"instruction": instruction}},
        upsert=True
    )

def reschedule_appointment(appointment_id,date):
    appointments.update_one(
            {"appointment_id":appointment_id},
            {"$set":{"booked_datetime":date}}
            )

def cancel_appointment(appointment_id):
    appointments.update_one(
            {"appointment_id":appointment_id},
            {"$set":{"cancelled":True}}
            )

def set_appointment(_id,appointment,owner_id):
    temp = appointment.copy()
    temp["user_id"] = _id
    temp["owner_id"] = owner_id
    temp["cancelled"] = False
    temp = appointments.insert_one(temp)
    return temp.inserted_id

def send_notification(_id,note,owner_id):
    notification = {"user_id":_id,"owner_id":owner_id,"note":note.get("Note"),"viewed":False,"created_at":str(datetime.now()),"details":note}
    profile = actions.get_profile(_id)
    notification["name"] = profile["name"]
    notification["username"] = profile["username"]
    notifications.insert_one(notification)
    return None


def get_user_appointments(_id,owner_id,phone_number=None):
    query = {}
    if phone_number is None:
        query = {"user_id":_id,"owner_id":owner_id}
    else:
        query = {"phone_number":phone_number}
    user_appointments = appointments.find(query)
    appointment_list = []
    for user_appointment in list(user_appointments):
        if not user_appointment.get("cancelled"):
            user_appointment["_id"] = str(user_appointment["_id"])
            appointment_list.append(user_appointment)
    return list(appointment_list)

def get_dataset(owner_id):
    dataset_entry = Data.find_one({"_id":int(owner_id)})
    return dataset_entry.get("dataset") if dataset_entry else None

def get_business_data(_id):
     data = Data.find_one({"_id":int(_id)})
     dataset = data["dataset"]
     return dataset

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
def get_notifications(_id):
    n = notifications.find({"owner_id":_id})
    notis = []
    for notification in list(n):
        print(notification.get("_id"))
        notification["_id"] = str(notification.get("_id"))
        notis.append(notification)
    return notis
def read_notification(_id):
    obj_id = ObjectId(id_str)
    notifications.update_one({"_id":obj_id},{"$set":{"viewed":True}})

def delete_customer(_id,owner_id):
    Users.remove({"_id":_id,"owner_id":owner_id})

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
    pass
    info = send_notification(1124492214,"hello world",123)
    print(info)
