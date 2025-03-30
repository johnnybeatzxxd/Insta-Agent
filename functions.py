import requests
import json
from datetime import datetime, date, timedelta  
import calendar
import database

def get_information(key, owner_id):
    info = database.get_dataset(owner_id)
    if info is None:
        return "data not found:"
    return info[key]

def get_next_weekday_date(weekday_name, reference_date=None):
    if reference_date is None:
        reference_date = date.today()  

    weekday_name = weekday_name.lower()
    if len(weekday_name) == 3:
        for i, name in enumerate(calendar.day_abbr):
            if name.lower() == weekday_name:
                weekday_name = calendar.day_name[i].lower()
                break
        else:
            return None
    elif weekday_name not in [name.lower() for name in calendar.day_name]:
        return None

    try:
        target_weekday = [name.lower() for name in calendar.day_name].index(weekday_name)
        days_ahead = (target_weekday - reference_date.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7

        next_date = reference_date + timedelta(days=days_ahead)  
        return next_date

    except ValueError:
        return None

def availablity(date_input):
    """
    Checks availability for a given date or weekday. Supports "today", weekday names,
    "next [weekday]", and YYYY-MM-DD date formats.

    Args:
        date_input: The date or weekday to check.

    Returns:
        The availability data from the API, or an error message.
    """
    # Process the date input
    general = False
    if date_input.lower() == "general":
        general = True
        resolved_date = date.today()  
        date_input = "today"
    if date_input.lower() == "today":
        resolved_date = date.today()
    elif date_input.lower() == "tomorrow":
        resolved_date = date.today() + timedelta(days=1)
    elif date_input.lower() in [day.lower() for day in calendar.day_name] + [day.lower() for day in calendar.day_abbr]:
        resolved_date = get_next_weekday_date(date_input)
    elif date_input.lower().startswith("next "):
        try:
            weekday = date_input.split(" ")[1]
            resolved_date = get_next_weekday_date(weekday)
        except IndexError:
            return "Please provide a day after 'next' keyword"
    else:
        try:
            resolved_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD or a weekday name."

    if not resolved_date:
        general = True
        resolved_date = date.today()
        date_input = "today"

    # Convert date to required format (YYYYMMDD)
    formatted_date = resolved_date.strftime("%Y%m%d")

    url = f"https://www.schedulista.com/schedule/bartaesthetics/available_times_json?preview_from=https%3A%2F%2Fwww.schedulista.com%2Fsettings&service_id=1074592411&date={formatted_date}&time_zone=Eastern+Time+(US+%26+Canada)"

    if general:
        formatted_date = formatted_date[:-2] + "01"
        url = f"https://www.schedulista.com/schedule/bartaesthetics/available_days_json?preview_from=https%3A%2F%2Fwww.schedulista.com%2Fsettings&service_id=1074592366&start_date={formatted_date}&time_zone=Eastern+Time+(US+%26+Canada)&scan_to_first_available=true"

    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the original JSON response
        parsed_data = json.loads(response.text)
        
        # Process dates into human-readable format
        processed = {
            "today": {
                "date": date.today().strftime("%Y-%m-%d"),
                "day": date.today().strftime("%A")
            }
        }
        
        # Handle different response formats based on query type
        if general:
            # For "general" query - has available_days dictionary
            processed["available_days"] = [
                {
                    "date": datetime.strptime(d, "%Y%m%d").strftime("%Y-%m-%d"),
                    "day": datetime.strptime(d, "%Y%m%d").strftime("%A")
                } for d in parsed_data.get("available_days", {}).keys()
            ]
            
            if parsed_data.get("first_available_day"):
                processed["first_available_day"] = {
                    "date": datetime.strptime(parsed_data["first_available_day"], "%Y%m%d").strftime("%Y-%m-%d"),
                    "day": datetime.strptime(parsed_data["first_available_day"], "%Y%m%d").strftime("%A")
                }
            else:
                processed["first_available_day"] = None
        else:
            # For specific day query - has a list of available times
            if isinstance(parsed_data, list):
                processed["available_times"] = parsed_data
            else:
                # Handle unexpected response format
                processed["raw_response"] = parsed_data
        
        return json.dumps(processed, indent=2)
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching availability: {e}"

def is_time_available(appointment_time, schedule):
    for slot in schedule.get("available_times"):
        slot_time = slot["start_time"][:19]  # Extract only the YYYY-MM-DDTHH:MM:SS part

        # Convert both times to a common format
        formatted_slot_time = datetime.strptime(slot_time, "%Y-%m-%dT%H:%M:%S")

        try:
            formatted_appointment_time = datetime.strptime(appointment_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            formatted_appointment_time = datetime.strptime(appointment_time, "%Y-%m-%d %H:%M")  # Handle missing seconds

        if formatted_slot_time == formatted_appointment_time:
            return True

    return False

if __name__ == "__main__":
    sche = {'today': {'date': '2025-03-30', 'day': 'Sunday'}, 'available_times': [{'start_time': '2025-03-31T09:00:00-0400', 'provider_id'
: 1074001982}, {'start_time': '2025-03-31T12:30:00-0400', 'provider_id': 1074001982}, {'start_time': '2025-03-31T13:00:00-0400'
, 'provider_id': 1074001982}, {'start_time': '2025-03-31T15:00:00-0400', 'provider_id': 1074001982}]}
    print(is_time_available("2025-03-31 12:40",sche))
    pass
