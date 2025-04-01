import json
from logging import raiseExceptions
import database
import datetime
import time
import requests
import os
from dotenv import load_dotenv
import traceback

import functions
load_dotenv(override=True)

gemini_api_key = os.environ.get('GeminiProKey')
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={}".format(gemini_api_key)
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
                        "enum": ["businessDescription", "booking","services","training","policy","payment_informations","contact"] ,
                        "description": 'you specify what information you want to get. you must choose one of this ["businessDescription", "booking","services","training","policy","payment_informations","contact"] use businessDescription for general info.'
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
                        "description": "The date for checking availability. Can be a specific date in YYYY-MM-DD format or a weekday name (e.g., 'Monday', 'next Friday', 'Tue','today'.'tomorrow','general').'examples': ['2025-03-10', 'Monday', 'next wednesday','today','tomorrow','general'] you can also use the 'general' this will return available dates with in current month you should use this often!",
                    },
                
                },
                "required": ["date"],
            }
        },
        {
            "name": "book_appointment",
            "description": "This function lets you book an appointment for the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "The name of the service booked.",
                    },
                    "deposit_amount": {
                        "type": "number",
                        "description": "deposit that the user made in the screenshot for lock the appointment",
                    },
                    "deal_price": {
                        "type": "number",
                        "description": "The deal price or discounted price of the service booked if any.",
                    },
                    "booked_datetime": {
                        "type": "string",
                        "description": "The date of the appointment.YYYY-MM-DD'T'HH:mm:ss format!",
                    },
                    "name": {
                        "type": "string",
                        "description": "The customer's full name.",
                    },
                    "phone_number": {
                        "type": "string",
                        "description": "The customer's phone number in this format +442012345678.it should be atleast 10 digit.",
                    },
                    "note":{
                        "type": "string",
                        "description": "short discription about the appointment. should include service name,user name, deposit_amount,deal_price",
                        }
                },
                "required": ["service", "deposit_amount","deal_price", "booked_datetime", "name", "phone_number"],
            }
        },
        {
            "name": "get_user_appointments",
            "description": "This function returns list of user appointments. phone_number is not required the system knows the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "phone_number is not required to call this function"
                    },
                
                },
            }
        },
        {
            "name": "reschedule_appointment",
            "description": "This function lets you reschedule appointment. it takes appointment_id of the appointment and date time. dont not ask the user for an id you should call get_user_appointments function first. availablity must be checked before calling this function",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "the appointment_id of the appointment fetched from get_user_appointments function"
                    },
                    "client_id": {
                        "type": "string",
                        "description": "client_id fetched from get_user_appointments function"
                    },
                    "date_time": {
                        "type": "string",
                        "description": "date time of the new rescheduled appointment in YYYY-MM-DD'T'HH:mm format!"
                    },
                },
                "required": ["appointment_id","client_id","date_time"],
            }
        },
        {
            "name": "cancel_appointment",
            "description": "This function lets you cancel an appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "the appointment_id of the appointment fetched from get_user_appointments function"
                    },
                },
                "required": ["appointment_id"],
            },
        },

]

class llm:

    def __init__(self,owner_id):
        self.owner_id = owner_id
        self.responseType = "text"
        self.function_descriptions = function_descriptions
        self.instruction = database.get_instruction(owner_id)

    def function_call(self,response,_id,owner_id):
        
        function_call = response["functionCall"]
        function_name = function_call["name"]
        function_args = function_call["args"]
        print(function_name)
        print(function_args)
    
        if function_name == "get_information": 
            info = function_args.get("info")
            
            if info:
                returned_info = functions.get_information(info,self.owner_id)
                return {"function_response":str(returned_info),"image":None}
                
            else:
                return {"function_response":"information type is required","image":None}

        if function_name == "check_availablity":
            date = function_args.get("date")
            if date:
                available_on = functions.availablity(date)
                return {"function_response":f"this are the times we are available suggest the user the earliest time:\n{available_on}","image":None}

        if function_name == "book_appointment": 
            ap = function_args 
            ap["payment_confirmed"] = False
            response = functions.book_appointment(_id,ap,owner_id)
            
            return {"function_response":response,"image":None}

        if function_name == "get_user_appointments":
            phone_number = function_args.get("phone_number",None)
            user_appointments = database.get_user_appointments(_id,owner_id,phone_number=phone_number)
            return {"function_response":user_appointments,"image":None}

        if function_name == "reschedule_appointment":
            date_time = function_args.get("date_time")
            appointment_id = function_args.get("appointment_id")
            client_id = function_args.get("client_id")
            duration = function_args.get("duration","60")
            date = date_time[:10]
            available_on = json.loads(functions.availablity(date))

            print(available_on)
            if functions.is_time_available(date_time, available_on):
                user_appointments = database.reschedule_appointment(appointment_id,date_time)
                reschedule_appointment = functions.reschedule_appointment(client_id,appointment_id,date_time,duration)

                return {"function_response":"appointment rescheduled!","image":None}
            return {"function_response":"error: specified date is not available","image":None}

        if function_name == "cancel_appointment":
            _id = function_args.get("_id")
            user_appointments = database.cancel_appointment(_id)
            return {"function_response":"the appointment has been cancelled!","image":None}


    def generate_response(self,_id,messages,owner_id):
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
                "temperature": 0,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048,
                "stopSequences": [],
                #'safety_settings': [{"category":"HARM_CATEGORY_DEROGATORY","threshold":4},{"category":"HARM_CATEGORY_TOXICITY","threshold":4},{"category":"HARM_CATEGORY_VIOLENCE","threshold":4},{"category":"HARM_CATEGORY_SEXUAL","threshold":4},{"category":"HARM_CATEGORY_MEDICAL","threshold":4},{"category":"HARM_CATEGORY_DANGEROUS","threshold":4}]
              },}
    
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
                        return response_data
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

    def process_query(self,_id,messages,owner_id):

        # generate a response for the query
        response = self.generate_response(_id,messages,owner_id)

        function_calls = []
        final_response = []

        for part in response["candidates"][0]["content"]["parts"]:
            if "functionCall" in part:
                function_calls.append(part)
            if "text" in part:
                final_response.append(part["text"])
                messages.append({
                    "role": "model",
                    "parts": part
                })

        while len(function_calls) > 0:

            for function in function_calls:
                # Process this function call
                function_name = function["functionCall"]["name"]
                function_args = function["functionCall"]["args"]
                print(f"calling function: {function_name}")
                # Execute the function
                function_response = self.function_call(function, _id,owner_id)
                function_response_message = function_response["function_response"]
                
                # Add the function call and response to the conversation history
                function = [{
                    "functionCall": {
                        "name": function_name,
                        "args": function_args
                    }
                }]
                functionResponse = [{
                    "functionResponse": {
                        "name": function_name,
                        "response": {
                            "name": function_name,
                            "content": function_response_message
                        }
                    }
                }]
                
                # Update messages for next API call (but don't save to database yet)

                func_call = {
                    "role": "model",
                    "parts": function
                }

                func_response = {
                    "role": "function",
                    "parts": functionResponse
                }

                messages.append(func_call)
                messages.append(func_response)

                database.add_message(_id, [func_call], owner_id,"model")
                database.add_message(_id, [func_response], owner_id,"function")
            # add the function response in the contenxt and database 
            print(messages)
            

            # generate response using the function call returns
            function_calls = []
            response = self.generate_response(_id,messages,owner_id)
            for part in response["candidates"][0]["content"]["parts"]:
                if "functionCall" in part:
                    function_calls.append(part)
                if "text" in part:
                    final_response.append(part["text"])
        return final_response

# messages = [] 
# while True:
#     user_msg = input("User: ")
#     message = {"role":"user","parts":[{"text":user_msg}]}
#     messages.append(message)
#     print(messages)
#     ai = llm()
#     response = ai.generate_response(123,messages)
#     print(ai)
