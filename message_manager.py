import json
import os
from dotenv import load_dotenv
from actions import send_text_message
import actions
import database
import ai
import time
import random

load_dotenv(override=True)

owner_id = os.environ.get("owner_id")

def process_messages(request):
    code = random.randint(0,10)
    print(f"Function {code} started!")
    owner_id = request["entry"][0]["id"]
    sender = request["entry"][0]["messaging"][0]["sender"]["id"]
    receiver = request["entry"][0]["messaging"][0]["recipient"]["id"]
    message_obj = request["entry"][0]["messaging"][0]

    if sender == str(owner_id):  # The owner sent a message
        print(f"Message sent to {receiver}")
    if receiver == str(owner_id):  # The owner received a message
        print(f"Message received from {sender}")

        prompt = []
        message = message_obj["message"]
        attachments = message.get("attachments", None)
        if attachments:
            for attachment in attachments:
                if attachment["type"] == "image":
                    image_url = attachment["payload"]["url"]
                    prompt.append({
                          "inline_data": {
                            "mime_type":"image/jpeg",
                            "data": actions.image_to_base64(image_url)
                          }})
        else:
            prompt.append({"text": message["text"]})

        current_conversation = database.add_message(sender, prompt, "user")
        print(f"function {code} saved the message!")

        # Use asyncio.sleep instead of time.sleep for async execution
        time.sleep(5)
        
        latest_conversation = database.get_conversation(sender)

        print(f"comparing the old convo: {current_conversation}\nlatest convo:{latest_conversation}")
        if current_conversation == latest_conversation:
            llm = ai.llm()
            print("Conversation going to the ai:", latest_conversation)
            response = llm.generate_response(sender,latest_conversation) 
            ai_response = [{"text":response}]

            database.add_message(sender,ai_response,"model")

            actions.send_text_message(sender,response)
        else:
            print(f"function {code} is late!")

if __name__ == "__main__":
    database.reset_conversation(1660159627957434)
    print("Database reset done!")

