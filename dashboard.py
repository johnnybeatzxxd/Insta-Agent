import database
import actions
import json
import os
from datetime import datetime, timedelta

cache_expiration_minutes = 10

def is_cache_valid(cache_file):
    """Check if cache file exists and is not expired"""
    if not os.path.exists(cache_file):
        return False
    
    try:
        with open(cache_file, "r") as f:
            cache_data = json.load(f)
            
        cache_time = datetime.fromisoformat(cache_data["time"])
        current_time = datetime.now()
        
        # Check if cache is still valid (less than expiration time)
        return current_time - cache_time < timedelta(minutes=cache_expiration_minutes)
    except (json.JSONDecodeError, KeyError, ValueError):
        return False

def transform_conversations(filtered_conversations, owner_id):
    conversations = []
    
    for i, conversation in enumerate(filtered_conversations):
        if "messages" not in conversation or "data" not in conversation["messages"]:
            continue
            
        # Find the other participant (not the owner)
        other_participant = None
        for participant in conversation["participants"]["data"]:
            if str(participant["id"]) != str(owner_id):
                other_participant = participant
                break
                
        if not other_participant:
            continue
            
        # Get all messages
        messages = []
        for msg in conversation["messages"]["data"]:
            message_time = datetime.strptime(msg["created_time"], "%Y-%m-%dT%H:%M:%S%z")
            formatted_time = message_time.strftime("%I:%M %p")
            
            messages.append({
                "id": len(messages) + 1,
                "content": msg.get("message", ""),
                "isUser": str(msg["from"]["id"]) == str(owner_id),
                "time": formatted_time
            })
        
        # Get last message info
        messages.reverse()
        last_message = messages[-1]["content"] if messages else ""
        last_message_time = messages[-1]["time"] if messages else ""
        
        conversations.append({
            "id": i + 1,
            "user": other_participant["username"].title().replace(".", " "),
            "avatar": "".join([name[0] for name in other_participant["username"].split()[:2]]).upper(),
            "lastMessage": last_message,
            "time": last_message_time,
            "unread": False,  # You can modify this based on your read/unread logic
            "messages": messages
        })
    
    return conversations

def dashboard_stats(owner_id,access_token):
    # Create ID-specific cache filenames
    users_cache_file = f"users_cache_{owner_id}.json"
    conversations_cache_file = f"conversations_cache_{owner_id}.json"
    
    # Check for users cache for this specific ID
    if is_cache_valid(users_cache_file):
        with open(users_cache_file, "r") as f:
            cache_data = json.load(f)
            users = cache_data["users"]
    else:
        # If cache invalid or doesn't exist, fetch from database
        users_cursor = database.get_users(owner_id)
        # Convert MongoDB cursor to list to make it JSON serializable
        users = list(users_cursor)
        users_cache = {
            "time": datetime.now().isoformat(),
            "users": users
        }
        with open(users_cache_file, "w") as f:
            json.dump(users_cache, f, indent=4, default=str)
    
    total_conversations = sum(len(user.get('conversation', [])) for user in users)
    
    user_ids = []
    for user in users:
        user_id = user['_id']
        user_ids.append(user_id)
        conv_count = len(user.get('conversation', []))
    
    # Check for conversations cache for this specific ID
    if is_cache_valid(conversations_cache_file):
        with open(conversations_cache_file, "r") as f:
            cache_data = json.load(f)
            filtered_conversations = cache_data["conversations"]
    else:
        # Get Instagram conversations and parse for our users
        insta_conversations = actions.get_conversations(access_token)
        filtered_conversations = []
        for conversation in insta_conversations["data"]:
            participant_ids = [int(participant["id"]) for participant in conversation["participants"]["data"]]
            if any(str(user_id) in map(str, participant_ids) for user_id in user_ids):
                filtered_conversations.append(conversation)
        
        # Save the new cache with ID-specific filename
        cache = {
            "time": datetime.now().isoformat(),
            "conversations": filtered_conversations
        }
        with open(conversations_cache_file, "w") as f:
            json.dump(cache, f, indent=4, default=str)

    # Parse recent chats from filtered conversations
    recent_chats = parse_recent_chats(filtered_conversations, owner_id)
    customers = []
    active_users = list(database.get_active_users(owner_id))  # Convert cursor to list
    for i, conversation in enumerate(filtered_conversations):
        other_participant = None
        for participant in conversation["participants"]["data"]:
            if str(participant["id"]) != str(owner_id):
                other_participant = participant
                break
                
        if not other_participant:
            continue
        
        if "messages" in conversation and "data" in conversation["messages"] and conversation["messages"]["data"]:
            recent_message = conversation["messages"]["data"][0]
            message_time = datetime.strptime(recent_message["created_time"], "%Y-%m-%dT%H:%M:%S%z")
            current_time = datetime.now(message_time.tzinfo)
            time_diff = current_time - message_time
            
            # Format last active time
            if time_diff.days > 0:
                last_active = message_time.strftime("Yesterday, %I:%M %p")
            else:
                last_active = message_time.strftime("Today, %I:%M %p")
        else:
            last_active = "N/A"
            
        # Get conversation count for this user
        conv_count = 0
        for user in users:
            if str(user['_id']) == str(other_participant['id']):
                conv_count = len(user.get('conversation', []))
                break

        bot_enabled = False
        for active_user in active_users:
            print(f"Comparing {active_user['_id']} with {other_participant['id']}")  # Debug print
            if str(active_user["_id"]) == str(other_participant["id"]):
                print(f"Match found: {active_user['_id']} - Active: {active_user.get('active', False)}")  # Debug print
                if active_user.get("active", False):
                    bot_enabled = True
                    break  

        # Create customer data
        username = other_participant["username"]
        print(username)
        print(bot_enabled)
        customers.append({
            "id": i + 1,
            "userId": other_participant["id"],
            "name": username.title().replace(".", " "),
            "avatar": "".join([name[0] for name in username.split()[:2]]).upper(),
            "username": f"{username}",
            "phone": "-",
            "conversations": conv_count,
            "lastActive": last_active,
            "botEnabled": bot_enabled,  
            "status": "active"  
        })

    # Transform conversations to the new format
    transformed_conversations = transform_conversations(filtered_conversations, owner_id)
    
    # Find owner information from participants
    owner_info = None
    for conversation in filtered_conversations:
        for participant in conversation["participants"]["data"]:
            if str(participant["id"]) == str(owner_id):
                owner_info = participant
                break
        if owner_info:
            break

    print(owner_info)
    # Create owner object
    owner_object = {
        "id": owner_id,
        "username": owner_info.get("username", "Unknown") if owner_info else "Unknown",
        "avatar": "".join([name[0] for name in owner_info.get("username", "Owner").split()[:2]]).upper() if owner_info else "O"
    }

    # Add owner to response
    response = {
        "owner": owner_object,
        "stats":[
        {
            "title": "Total Users",
            "value": f"{len(users)}",
            "description": "Active Instagram followers",
            "icon": "Users",
            "change": "+100%",
            "color": "bg-salon-100 text-salon-700",
        },
        {
            "title": "Conversations",
            "value": f"{total_conversations}",
            "description": "Last 90 days",
            "icon": "MessageCircle",
            "change": "+100%",
            "color": "bg-salon-100 text-salon-700",
        },
        {
            "title": "Unresolved",
           "value": "0",
           "description": "Needs attention",
           "icon": "AlertTriangle",
           "change": "+0.0%",
           "color": "bg-amber-100 text-amber-700",
        }
    ],
    "recent_chats": recent_chats,
    "customers": customers,
    "conversations": transformed_conversations
}
    return response 

def parse_recent_chats(filtered_conversations, owner_id):
    # Parse recent chats from filtered conversations
    recent_chats = []
    
    for i, conversation in enumerate(filtered_conversations):
        if "messages" not in conversation or "data" not in conversation["messages"] or not conversation["messages"]["data"]:
            continue
            
        # Find the other participant (not the owner)
        other_participant = None
        for participant in conversation["participants"]["data"]:
            # Compare with owner_id instead of hardcoded username
            if str(participant["id"]) != str(owner_id):
                other_participant = participant
                break
                
        if not other_participant:
            continue
            
        # Get the most recent message
        recent_message = conversation["messages"]["data"][0]
        
        # Calculate time difference
        message_time = datetime.strptime(recent_message["created_time"], "%Y-%m-%dT%H:%M:%S%z")
        current_time = datetime.now(message_time.tzinfo)
        time_diff = current_time - message_time
        
        # Format time difference
        if time_diff.days > 0:
            time_formatted = f"{time_diff.days} {'day' if time_diff.days == 1 else 'days'} ago"
        elif time_diff.seconds // 3600 > 0:
            hours = time_diff.seconds // 3600
            time_formatted = f"{hours} {'hour' if hours == 1 else 'hours'} ago"
        elif time_diff.seconds // 60 > 0:
            minutes = time_diff.seconds // 60
            time_formatted = f"{minutes} min ago"
        else:
            time_formatted = "just now"
        
        # Format message summary (truncate if too long)
        message_text = recent_message.get("message", "")
        
        # Determine what type of interaction it was based on message content
        if message_text.lower().startswith("do you"):
            message_type = "Inquired about"
        elif "price" in message_text.lower() or "cost" in message_text.lower() or "how much" in message_text.lower():
            message_type = "Requested pricing information"
        elif "appointment" in message_text.lower() or "book" in message_text.lower() or "schedule" in message_text.lower() or "time" in message_text.lower():
            message_type = "Asked about appointment availability"
        elif "product" in message_text.lower() or "recommend" in message_text.lower():
            message_type = "Asked about product recommendations"
        elif "service" in message_text.lower() or "lash" in message_text.lower() or "hair" in message_text.lower():
            message_type = "Asked about hair styling services"
        else:
            message_type = "Sent a message"
        
        # Add to recent chats
        recent_chats.append({
            "id": i + 1,
            "user": other_participant["username"],
            "message": message_type,
            "time": time_formatted
        })
    
    # Limit to most recent 4 chats
    recent_chats = recent_chats[:4]
    
    return recent_chats 
