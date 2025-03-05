import os 
from dotenv import load_dotenv


load_dotenv(override=True)

owner_id = os.environ.get("owner_id")
def process_messages(request):
    print("getting processed:",request)
    owner_id = request["entry"][0]["id"]
    sender =  request["entry"][0]["messaging"][0]["sender"]["id"]
    receiver = request["entry"][0]["messaging"][0]["recipient"]["id"]
    message_obj = request["entry"][0]["messaging"][0]

    if sender == str(owner_id): # The owner sent a message
        print(f"message sent to {receiver}")
    if receiver == str(owner_id): # The owner recevied a message
        print(f"message received from {sender}")



    

