import json
from logging import raiseExceptions
import database
import datetime
import time
import os
from dotenv import load_dotenv
import traceback
# Remove OpenAI import if present
# from openai import OpenAI, APIConnectionError # Assuming this or similar was used before
import anthropic # Import Anthropic SDK

# Import SimpleNamespace for the adapter
from types import SimpleNamespace 

import functions
load_dotenv(override=True)
ModelName = os.getenv('ModelName')
Temperature = float(os.environ.get('Temperature'))
API_KEY = os.getenv("AI_API_KEY")
# ModelUrl = os.getenv("ModelUrl") # Not typically used with Anthropic SDK client
today = datetime.date.today()
year = today.year
month = today.month
day = today.day

tools = [
    {
            "name": "get_information",
            "description": "this function gives any information you need to answer users questions.",
        "input_schema": {
                "type": "object",
                "properties": {
                    "info": {
                        "type": "string",
                        "enum": ["businessDescription", "booking","services","training","policy","payment_informations","contact"],
                        "description": 'you specify what information you want to get. you must choose one of this ["businessDescription", "booking","services","training","policy","payment_informations","contact"] use businessDescription for general info.'
                    },
                },
            "required": ["info"]
        }
    },
    {
            "name": "check_availablity",
            "description": "This function lets you check availability within a specified date. The date can be provided as a specific date (YYYY-MM-DD) or as a weekday name (e.g., 'Monday', 'next Tuesday'). If a weekday name is provided, it will be interpreted as the next occurrence of that weekday.",
        "input_schema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date for checking availability. Can be a specific date in YYYY-MM-DD format or a weekday name (e.g., 'Monday', 'next Friday', 'Tue','today'.'tomorrow','general').'examples': ['2025-03-10', 'Monday', 'next wednesday','today','tomorrow','general'] you can use 'general' for next week it will return available dates with in current month you should use this often!",
                    },
                },
            "required": ["date"]
        }
    },
    {
            "name": "book_appointment",
            "description": "This function lets you book an appointment for the user",
        "input_schema": {
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
                        "description": "The customer's phone number. it should be atleast 10 digit.",
                    },
                    "email":{
                        "type":"string",
                        "description": "email of the customer",
                        },
                    "note":{
                        "type": "string",
                        "description": "discription about the appointment. should include service name,user name, deposit_amount,deal_price",
                    }
                },
                         "required": ["service", "deposit_amount","deal_price", "booked_datetime", "name","email", "phone_number","note"]
        }
    },
    {
            "name": "get_user_appointments",
            "description": "This function returns list of user appointments. phone_number is not required the system knows the user",
        "input_schema": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "phone_number is not required to call this function"
                },
            }
        }
    },
    {
            "name": "reschedule_appointment",
            "description": "This function lets you reschedule appointment. it takes appointment_id of the appointment and date time. dont not ask the user for an id you should call get_user_appointments function first. availablity must be checked before calling this function",
        "input_schema": {
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
            "required": ["appointment_id","client_id","date_time","note"]
        }
    },
    {
            "name": "cancel_appointment",
            "description": "This function lets you cancel an appointment",
        "input_schema": {
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
            "required": ["appointment_id","note"]
        }
    },
    {
            "name": "get_examples",
            "description": "This function allows you to get images of specific services as an example so you can sent the link to the customers",
        "input_schema": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "enum": ["classic", "hybrid","mega","training","policy","payment_informations","contact"],
                        "description": "service you want to send example"
                    },
                },
            "required": ["service"]
        }
    }
]

class llm:
    def __init__(self,owner_id):
        self.owner_id = owner_id
        self.responseType = "text"
        self.tools = tools
        self.instruction = database.get_instruction(owner_id)
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(
            api_key=API_KEY, # Uses the existing environment variable
        )

    # DO NOT TOUCH this function per user request
    def function_call(self,response,_id,owner_id):
        function_name = response.function.name
        function_args = json.loads(response.function.arguments)
        print(function_name)
        print(function_args)
    
        if function_name == "get_information": 
            info = function_args.get("info")
            
            if info:
                returned_info = functions.get_information(info,_id,owner_id)
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
                try:
                    user_appointments = database.reschedule_appointment(appointment_id,date_time)
                except Exception as e:
                    print("error while saving reschedule:",e)
                try:
                    reschedule_appointment = functions.reschedule_appointment(client_id,appointment_id,date_time,duration)
                except Exception as e:
                    print("error while reschudling in schedulista:",e)
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

        if function_name == "get_examples":
            query = function_args.get("service")
            result = functions.send_example(query,owner_id)
            return {"function_response": f"send the user one of those link: {result}","image":None}

    def generate_response(self,_id,messages,owner_id):
        max_retries = 3
        retry_delay = 3 # seconds

        for attempt in range(max_retries):
            try:
                # Use Anthropic's client.messages.create
                response = self.client.messages.create(
                    model=ModelName,
                    max_tokens=1024, 
                    temperature=Temperature,
                    system=self.instruction, 
                    messages=messages, 
                    tools=self.tools,
                    tool_choice={"type": "auto"} 
                )
                # print("Anthropic response:", response) 
                return response # Success, return the response
            except Exception as e: 
                print(f"Attempt {attempt + 1} failed with error during Anthropic API call: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Max retries reached. Raising the error.")
                    traceback.print_exc() # Print traceback for debugging the final error
                    raise # Re-raise the exception after the last attempt

    def process_query(self,_id,messages,owner_id):
        new_messages_for_db = [] 
        current_conversation = messages.copy()
        
        while True:
            print(f"Calling Anthropic API for {_id}. Conversation length: {len(current_conversation)}")
            response = self.generate_response(_id, current_conversation, owner_id)

            # --- Construct Assistant Message ---
            # Start with role, get text content later
            assistant_message_content = []
            stop_reason = response.stop_reason
            
            # Extract text content if present
            text_content = "".join([block.text for block in response.content if block.type == 'text'])
            if text_content:
                assistant_message_content.append({"type": "text", "text": text_content})

            # Store the full assistant message structure (including potential tool_use later)
            assistant_msg_to_save = {
                "role": "assistant",
                "content": assistant_message_content # Start with text, add tool_use if needed
            }
            
            # --- Check for Tool Use ---
            tool_use_blocks = [block for block in response.content if block.type == 'tool_use']

            if not tool_use_blocks:
                 # If no tool use, just save the text response and finish
                 print(f"Anthropic response for {_id}: Text only.")
                 current_conversation.append(assistant_msg_to_save) # Add to temporary conversation state
                 new_messages_for_db.append(assistant_msg_to_save) # Add to messages to be saved
                 break # Exit the loop, final response generated
            else:
                # --- Handle Tool Use ---
                print(f"Anthropic response for {_id}: Tool use required ({len(tool_use_blocks)} tools).")
                # Flag to determine if messages related to this tool call should be saved
                should_save_messages = False 
                # Add the raw tool_use blocks to the assistant message content
                for tool_use in tool_use_blocks:
                     func_call = {
                         "type": "tool_use",
                         "id": tool_use.id,
                         "name": tool_use.name,
                         "input": tool_use.input
                     }
                     assistant_message_content.append(func_call)
                     print(tool_use.name)
                     # Set flag if 'check_availablity' is used
                     if tool_use.name in ["check_availablity","book_appointment","reschedule_appointment","cancel_appointment","get_user_appointments"]:
                         should_save_messages = True # Rename flag for clarity
                
                current_conversation.append(assistant_msg_to_save) # Add assistant msg with tool_use to current state
                new_messages_for_db.append(assistant_msg_to_save) # Add to messages to be returned (always)

                # --- Prepare Tool Results ---
                tool_results_content = []
                for tool_use in tool_use_blocks:
                    # Create the adapter object to mimic the old structure for function_call
                    # The arguments need to be a JSON string for the existing function_call
                    shim_arguments_json = json.dumps(tool_use.input)
                    adapter = SimpleNamespace(
                        function=SimpleNamespace(
                            name=tool_use.name,
                            arguments=shim_arguments_json
                        )
                    )
                    
                    print(f"Calling function: {tool_use.name} with input: {tool_use.input}")
                    # Call the original function_call with the adapter
                    function_response_data = self.function_call(adapter, _id, owner_id)
                    # Extract the string response content
                    function_response_content = str(function_response_data.get("function_response", "")) # Ensure string
                    print(f"Extracted function response content: '{function_response_content}'") # <-- Print extracted content
                    
                    # Append the result in Anthropic's tool_result format
                    func_response = {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": function_response_content
                    }
                    tool_results_content.append(func_response)
                
                # Create the user message containing all tool results
                tool_results_msg = {
                    "role": "user", # Use 'user' role for tool results per Anthropic spec
                    "content": tool_results_content 
                }
                                
                current_conversation.append(tool_results_msg) # Add tool results message to conversation state
                new_messages_for_db.append(tool_results_msg) # Add tool results message to the list for return (always)

                # Conditionally save BOTH the assistant's tool_use request AND the tool results message
                if should_save_messages:
                    print(f"Saving assistant tool request and tool results for {_id} because 'check_availablity' was called.")
                    # Save the assistant message that requested the tool use
                    database.add_message(_id,[assistant_msg_to_save],owner_id)
                    # Save the user message containing the tool results
                    database.add_message(_id,[tool_results_msg],owner_id)
                else:
                    print(f"Skipping save for assistant tool request and tool results for {_id} ('check_availablity' not called).")
                
                # Continue the loop to send results back to the model
                print(f"Looping back to Anthropic API for {_id} with tool results.")


        # Return the list of messages (assistant responses + tool results) added during this processing turn
        print(f"Finished processing query for {_id}. Returning {len(new_messages_for_db)} new messages.")
        print(new_messages_for_db)
        return new_messages_for_db

