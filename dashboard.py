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

    print(recent_chats)
    response = {
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
    "recent_chats": recent_chats
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
