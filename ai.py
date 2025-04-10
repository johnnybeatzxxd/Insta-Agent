import json
from logging import raiseExceptions
import database
import datetime
import time
import os
from dotenv import load_dotenv
import traceback
from openai import OpenAI, APIConnectionError

import functions
load_dotenv(override=True)

today = datetime.date.today()
year = today.year
month = today.month
day = today.day

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_information",
            "description": "this function gives any information you need to answer users questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "info": {
                        "type": "string",
                        "enum": ["businessDescription", "booking","services","training","policy","payment_informations","contact"],
                        "description": 'you specify what information you want to get. you must choose one of this ["businessDescription", "booking","services","training","policy","payment_informations","contact"] use businessDescription for general info.'
                    },
                },
                "required": ["info"],
            }
        }
    },
    {
        "type": "function",
        "function": {
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
        }
    },
    {
        "type": "function",
        "function": {
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
                        "description": "discription about the appointment. should include service name,user name, deposit_amount,deal_price",
                    }
                },
                "required": ["service", "deposit_amount","deal_price", "booked_datetime", "name", "phone_number","note"],
            }
        }
    },
    {
        "type": "function",
        "function": {
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
        }
    },
    {
        "type": "function",
        "function": {
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
                    "previous_date": {
                        "type": "string",
                        "description": "the old date"
                    },
                    "date_time": {
                        "type": "string",
                        "description": "date time of the new rescheduled appointment in YYYY-MM-DD'T'HH:mm format!"
                    },
                    "note": {
                        "type": "string",
                        "description": "discription about the client and rescheduled appointment include user info like name, phone number and service name"
                    },
                },
                "required": ["appointment_id","client_id","date_time","note"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "This function lets you cancel an appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "the appointment_id of the appointment fetched from get_user_appointments function"
                    },
                    "note": {
                        "type": "string",
                        "description": "discription about the client and cancelled appointment. include user info like name, phone number and service name"
                    },
                    "date": {
                        "type": "string",
                        "description": "cancelled date"
                    },
                },
                "required": ["appointment_id","note"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_example",
            "description": "This function allows you to send images of specific services as an example",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "enum": ["classic", "hybrid","mega","training","policy","payment_informations","contact"],
                        "description": "service you want to send example"
                    },
                },
                "required": ["service"],
            }
        }
    }
]

class llm:
    def __init__(self,owner_id):
        self.owner_id = owner_id
        self.responseType = "text"
        self.tools = tools
        self.instruction = database.get_instruction(owner_id)
        self.client = OpenAI(
            api_key=os.environ.get('GptApiKey'),
            # base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

    def function_call(self,response,_id,owner_id):
        function_name = response.function.name
        function_args = json.loads(response.function.arguments)
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
            note = function_args.get("note")
            notification = {}
            detail = {}
            notification["type"] = "book appointment"
            detail["Service"] = function_args.get("service")
            detail["Appointment date"] = function_args.get("booked_datetime")
            detail["Deposit amount"] = function_args.get("deposit_amount")
            detail["Deal price"] = function_args.get("deal_price")
            detail["Phone number"] = function_args.get("phone_number")
            notification["Note"] = function_args.get("note")
            notification["details"] = detail

            response = functions.book_appointment(_id,ap,owner_id)
            notification = database.send_notification(_id,notification,owner_id)
            
            return {"function_response":str(response),"image":None}

        if function_name == "get_user_appointments":
            phone_number = function_args.get("phone_number",None)
            user_appointments = database.get_user_appointments(_id,owner_id,phone_number=phone_number)
            return {"function_response":str(user_appointments),"image":None}

        if function_name == "reschedule_appointment":
            date_time = function_args.get("date_time")
            previous_date = function_args.get("previous_date")
            appointment_id = function_args.get("appointment_id")
            client_id = function_args.get("client_id")
            duration = function_args.get("duration","60")
            date = date_time[:10]
            notification = {}
            notification["note"] = function_args.get("note")
            notification["type"] = "reschedule appointment"
            details = {}
            details["Original date"] = previous_date
            details["Rescheduled to"] = date_time
            details["Note"] = function_args.get("note")
            notification["details"] = details
            available_on = json.loads(functions.availablity(date))

            if functions.is_time_available(date_time, available_on):
                user_appointments = database.reschedule_appointment(appointment_id,date_time)
                reschedule_appointment = functions.reschedule_appointment(client_id,appointment_id,date_time,duration)
                database.send_notification(_id,notification,owner_id)

                return {"function_response":"appointment rescheduled!","image":None}
            return {"function_response":"error: specified date is not available","image":None}

        if function_name == "cancel_appointment":
            appointment_id = function_args.get("appointment_id")
            notification = {}
            note = function_args.get("note")
            notification["type"] = "cancel appointment"
            notification["note"] = note
            details = {}
            details["Note"] = note
            notification["details"] = details
            user_appointments = database.cancel_appointment(appointment_id)
            schedulista = functions.cancel_appointment(appointment_id)
            notification = database.send_notification(_id,note,owner_id)
            return {"function_response":f"appointment has been cancelled! contact @iamtonybart for refund!","image":None}

        if function_name == "send_example":
            query = function_args.get("service")
            result = functions.send_example(query,owner_id)
            return {"function_response": result,"image":None}

    def generate_response(self,_id,messages,owner_id):
        system_message = {"role": "system", "content": self.instruction}
        msg = messages.copy()
        msg.insert(0, system_message)
        print(json.dumps(msg, indent=4))
        
        max_retries = 3
        retry_delay = 3 # seconds

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=msg,
                    tools=self.tools,
                    tool_choice="auto"
                )
                # print("response:",response)
                return response # Success, return the response
            except APIConnectionError as e:
                print(f"Attempt {attempt + 1} failed with connection error: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Max retries reached. Raising the connection error.")
                    raise # Re-raise the exception after the last attempt
            except Exception as e:
                # Catch any other exceptions
                print(f"Error generating response: {e}")
                raise # Re-raise other exceptions immediately

    def process_query(self,_id,messages,owner_id):
        # Keep track of messages added during this turn (assistant + tool responses)
        new_messages_for_db = [] 
        
        # Make a copy to avoid modifying the original list passed in, 
        # unless we intend for the caller to see the full internal state.
        current_conversation = messages.copy()
        
        while True:
            response = self.generate_response(_id, current_conversation, owner_id)
            response_message = response.choices[0].message
            
            # Add the raw assistant message (could have content or tool_calls)
            assistant_msg_to_save = {
                "role": "assistant",
                "content": response_message.content,
                # Ensure tool_calls are serializable if they exist
                "tool_calls": [tc.model_dump() for tc in response_message.tool_calls] if response_message.tool_calls else None
            }
            # Filter out None values for cleaner storage
            assistant_msg_to_save = {k: v for k, v in assistant_msg_to_save.items() if v is not None}
            
            current_conversation.append(assistant_msg_to_save)
            new_messages_for_db.append(assistant_msg_to_save)

            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_response_data = self.function_call(tool_call, _id, owner_id)
                    function_response_content = function_response_data["function_response"]
                    
                    tool_response_msg = {
                        "role": "tool",
                        "content": function_response_content,
                        "tool_call_id": tool_call.id
                    }
                    current_conversation.append(tool_response_msg)
                    new_messages_for_db.append(tool_response_msg)
                    
                    # Note: We don't add the tool response to final_response_content
                    # as it's not meant for the end user directly.
            else:
                # No more tool calls, this loop iteration is the end.
                break
                
        # Return the list of messages added during this processing turn
        return new_messages_for_db

