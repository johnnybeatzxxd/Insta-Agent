import json
import database
import datetime
import time
import requests
import os
from dotenv import load_dotenv
import traceback

import functions
load_dotenv()

gemini_api_key = os.environ.get('GeminiProKey')
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={}".format(gemini_api_key)
headers = {"Content-Type": "application/json",}


today = datetime.date.today()
year = today.year
month = today.month
day = today.day


function_descriptions = [
        {
            "name": "get_information",
            "description": "this function gives any information you need to answer users questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "info": {
                        "type": "string",
                        "enum": ["businessDescription", "booking","services","training","policy","payment_plans","contact"],
                        "description": 'you specify what information you want to get. you must choose one of this ["businessDescription", "booking","services","training","policy","payment_plans","contact"] use businessDescription for general info.'
                    },
                },
                "required": ["info"],
            }
        },
        {
            "name": "check_availablity",
            "description": "This function lets you check availability within a specified date. The date can be provided as a specific date (YYYY-MM-DD) or as a weekday name (e.g., 'Monday', 'next Tuesday'). If a weekday name is provided, it will be interpreted as the next occurrence of that weekday.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date for checking availability. Can be a specific date in YYYY-MM-DD format or a weekday name (e.g., 'Monday', 'next Friday', 'Tue','today'.'tomorrow').'examples': ['2025-03-10', ;Monday;, 'next wednesday','today','tomorrow']",
                    },
                
                },
                "required": ["date"],
            }
        },
]

class llm:

    def __init__(self):
        self.responseType = "text"
        self.function_descriptions = function_descriptions
        self.instruction = """You are the helpful and friendly AI assistant for Bartaesthetics, a beauty salon.
            Your primary goal is to assist customers with their questions and needs in a way that feels welcoming, professional, and efficient.
            Always be polite and use positive language. Speak concisely and clearly; avoid overly technical jargon unless the customer demonstrates understanding of it.
            Think of yourself as a virtual receptionist.if the conversation is new explain yourself who you are and who you work for.
            you also can process pictures of users and recommend our suitable services."""

    def function_call(self,response,_id):
        
        function_call = response["candidates"][0]["content"]["parts"][0]["functionCall"]
        function_name = function_call["name"]
        function_args = function_call["args"]
        print(function_name)
        print(function_args)
    
        if function_name == "get_information": 
            info = function_args.get("info")
            
            if info:
                returned_info = functions.get_information(info)
                print(returned_info)
                return {"function_response":str(returned_info),"image":None}
                
            else:
                return {"function_response":"information type is required","image":None}

        if function_name == "check_availablity":
            date = function_args.get("date")
            if date:
                available_on = functions.availablity(date)
                return {"function_response":f"this are the times we are available tell the user well:\n{available_on}","image":None}

        if function_name == "off_topic":
            return {"function_response":'you should only assist the user with only our property and business realted question.so dont assist! tell them to google it or somthing.',"image":None}
        else:
            return {"function_response":'function not found!'}


    def generate_response(self,_id,messages):
        data = {
                "contents": messages,
                "system_instruction": {
                      "parts": [
                        {
                          "text": self.instruction
                        }, 
                      ],
                      "role": "system" 
                    },
                "tools": [{
                    "functionDeclarations": function_descriptions
                    }],
                "safetySettings": [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
        ],
                "generationConfig": {
                "temperature": 0.1,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048,
                "stopSequences": [],
                #'safety_settings': [{"category":"HARM_CATEGORY_DEROGATORY","threshold":4},{"category":"HARM_CATEGORY_TOXICITY","threshold":4},{"category":"HARM_CATEGORY_VIOLENCE","threshold":4},{"category":"HARM_CATEGORY_SEXUAL","threshold":4},{"category":"HARM_CATEGORY_MEDICAL","threshold":4},{"category":"HARM_CATEGORY_DANGEROUS","threshold":4}]
              },}


        print("generating answer ... ")
        retries = 0
        max_retries = 3
        while retries < max_retries:
            try:
                print("Executing request...")
                response = requests.post(url, headers=headers, json=data)
                print(f"Status Code: {response.status_code}, Response Body: {response.text}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data:
                        print("Valid response received:")
                        break
                    else:
                        print("Empty JSON response received, retrying...")
                else:
                    print(f"Received non-200 status code: {response.status_code}")
                
                time.sleep(5)
            except requests.exceptions.RequestException as e:
                print(f'Request failed: {e}, retrying...')
                time.sleep(5)
            retries += 1
        
        if retries >= max_retries:
            raise Exception("Failed to get response from the model")
        while "functionCall" in response_data["candidates"][0]["content"]["parts"][0]:
            
            function_call = response_data["candidates"][0]["content"]["parts"][0]["functionCall"]
            function_name = function_call["name"]

            function_response = self.function_call(response_data,_id)
            function_response_message = function_response["function_response"]
            print(function_response_message)

            result = json.dumps(function_response)
            function = [{
                        "functionCall": {
                        "name": function_name,
                        "args": function_call["args"]
                                        }             
                            }]
            functionResponse = [{
                                "functionResponse":{
                                    "name": function_name,
                                    "response":{
                                        "name": function_name,
                                        "content": function_response_message
                                                }
                                                    }  
                                    },
                                    
                                    ]
            database.add_message(_id,function,"model")
            database.add_message(_id,functionResponse,"function")   
            messages.append({
                            "role": "model",
                            "parts": function
                            },)
            messages.append({"role": "function",
                            "parts": functionResponse
                                }) 
            retries = 0
            max_retries = 3
            while retries < max_retries:
                try:
                    print("Executing request...")
                    response = requests.post(url, headers=headers, json=data)
                    print(f"Status Code: {response.status_code}, Response Body: {response.text}")
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data:
                            print("Valid response received:", response_data)
                            break
                        else:
                            print("Empty JSON response received, retrying...")
                            ask_response = {"role": "user",
                                            "parts": [{"text": "??"}]
                                            }
                            if messages[-1] != ask_response:
                                messages.append(ask_response)
                                print(messages[-1])
                    else:
                        print(f"Received non-200 status code: {response.status_code}")
                    
                    retries += 1
                    time.sleep(5)
                except requests.exceptions.RequestException as e:
                    print(f'Request failed: {e}, retrying...')
                    retries += 1
                    time.sleep(5)
            

        return response_data["candidates"][0]["content"]["parts"][0]["text"]

# messages = [] 
# while True:
#     user_msg = input("User: ")
#     message = {"role":"user","parts":[{"text":user_msg}]}
#     messages.append(message)
#     print(messages)
#     ai = llm()
#     response = ai.generate_response(123,messages)
#     print(ai)
