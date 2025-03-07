import os 
from dotenv import load_dotenv
from actions import send_text_message
import database
import ai

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

        message = message_obj["message"]["text"]    
        prompt = [{"text":message}]
        # database.register(sender)

        conversation = database.add_message(sender,prompt,"user") 

        llm = ai.llm() 

        ai_response = llm.generate_response(sender,conversation)
        print("response:",ai_response)
        response = [{"text":ai_response}]

        database.add_message(sender,response,"model")

        response_message = response[0].get("text")

        
        send_text_message(sender,response_message)




    

