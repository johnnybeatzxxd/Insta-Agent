import requests
import os
from dotenv import load_dotenv


load_dotenv(override=True)
cookie = os.environ.get('schedulista_cookie')


headers = {
    "authority": "www.schedulista.com",
    "method": "POST",
    "path": "/calendar/create_appointment_v2",
    "scheme": "https",
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "cookie": cookie,
    "origin": "https://www.schedulista.com",
    "priority": "u=1, i",
    "referer": "https://www.schedulista.com/calendar/new",
    "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36",
    "x-csrf-token": "jvixQ6WAeumqjZOHKWL/7QVJfb4o7R2vOcFObbvTzrLTZpmjquR9RHDIhuCjls1TA8D03pFRkE6k5RLbLDJMyw==",
    "x-requested-with": "XMLHttpRequest"
}

def create_appointment(client_id,name,phone_number,start_time="",end_time="2025-04-02T10:00:00",duration="60",note=""):
    url = "https://www.schedulista.com/calendar/create_appointment_v2"
    payload = {
        "utf8": "✓",
        "authenticity_token": "jvixQ6WAeumqjZOHKWL/7QVJfb4o7R2vOcFObbvTzrLTZpmjquR9RHDIhuCjls1TA8D03pFRkE6k5RLbLDJMyw==",
        "appointment_id": "",
        "personal_appointment_id": "",
        "is_appointment_edit": "true",
        "orig_start_time": "",
        "business_id": "1073946337",
        "recurrence[formatted_recurrence_ends_on_date]": "",
        "provider_id": "1074007544",
        "is_gap_appointment": "false",
        "is_recurring_appointment": "false",
        "color": "",
        "service_id": "1074613752",
        "date": "20250330",
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "appointment[beginning_duration_minutes]": "5",
        "appointment[gap_duration_minutes]": "5",
        "appointment[finish_duration_minutes]": "5",
        "max_capacity": "",
        "recurrence[mode]": "none",
        "coupon_redemption_code": "",
        "recurrence[repeat_every_n_days]": "1",
        "recurrence[repeat_every_n_weeks]": "1",
        "recurrence[repeat_every_n_months]": "1",
        "recurrence[repeat_every_n_years]": "1",
        "recurrence[days][1]": "1",
        "recurrence[monthly_nth_day]": "-1",
        "recurrence[monthly_repeat_by]": "day_of_week",
        "recurrence[end_mode]": "never",
        "recurrence[ends_after_occurrences]": "10",
        "recurrence[ends_on_date]": "",
        "business_client_id": "",
        "client_search": "",
        "business_client[id]": f"{client_id}",
        "location": "",
        "appointment_notes": note,
        "send_client_notifications": "false",
        "personal_message": "",
        "update_all_future": "false"
    }

    response = requests.post(url, headers=headers, data=payload)

    print("Response Status Code:", response.status_code)
    print("Response Text:", response.text)
    return response.json()

def create_client(name,phone_number,email):
    url = "https://www.schedulista.com/clients/create_client"
    parts = name.split(" ")
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    payload = {
    "utf8": "✓",
    "authenticity_token": "jvixQ6WAeumqjZOHKWL/7QVJfb4o7R2vOcFObbvTzrLTZpmjquR9RHDIhuCjls1TA8D03pFRkE6k5RLbLDJMyw==",
    "business_client[first_name]": f"{first_name}",
    "business_client[last_name]": f"{last_name}",   
    "business_client[phone]": f"{phone_number}",
    "business_client[sms_on]": "0",
    "business_client[sms_reminder_lead_time_minutes]": "60",
    "business_client[email]": f"{email}",
    "business_client[time_zone]": "",
    "business_client[notes]": ""
    }

    response = requests.post(url, headers=headers, data=payload)
    print("Response Status Code:", response.status_code)
    print("Response Text:", response.text)
    return response.json()

def reschedule(client_id,appointment_id,start_time,end_time,duration):
    url = "https://www.schedulista.com/calendar/update_appointment_v2"
    payload = {
        "utf8": "✓",
        "authenticity_token": "jvixQ6WAeumqjZOHKWL/7QVJfb4o7R2vOcFObbvTzrLTZpmjquR9RHDIhuCjls1TA8D03pFRkE6k5RLbLDJMyw==",
        "appointment_id": appointment_id,
        "personal_appointment_id": "",
        "is_appointment_edit": "true",
        "orig_start_time": "",
        "business_id": "1073945781",
        "recurrence[formatted_recurrence_ends_on_date]": "",
        "is_gap_appointment": "false",
        "is_recurring_appointment": "false",
        "color": "",
        "service_id": "1074611095",
        "date": "20250331",
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "appointment[beginning_duration_minutes]": "5",
        "appointment[gap_duration_minutes]": "5",
        "appointment[finish_duration_minutes]": "5",
        "max_capacity": "",
        "recurrence[mode]": "none",
        "coupon_redemption_code": "",
        "recurrence[repeat_every_n_days]": "1",
        "recurrence[repeat_every_n_weeks]": "1",
        "recurrence[repeat_every_n_months]": "1",
        "recurrence[repeat_every_n_years]": "1",
        "recurrence[monthly_nth_day]": "-1",
        "recurrence[monthly_repeat_by]": "day_of_week",
        "recurrence[end_mode]": "never",
        "recurrence[ends_after_occurrences]": "10",
        "recurrence[ends_on_date]": "",
        "business_client_id": "",
        "client_search": "",
        "business_client[id]": client_id,
        "location": "",
        "appointment_notes": "",
        "send_client_notifications": True,
        "personal_message": "",
        "update_all_future": "false"
    }

    response = requests.post(url, headers=headers, data=payload)
    print("Response Status Code:", response.status_code)
    print("Response Text:", response.text)
    return response.json()

def cancel_appointment(appointment_id):
    url = 'https://www.schedulista.com/calendar/cancel_appointment_v2'
    payload = {
        "delete_mode": "instance",
        "send_client_notifications": True,
        "personal_message": "",
        "appointment_id": appointment_id,
        "is_no_show": False
    }

    response = requests.post(url, headers=headers, data=payload)
    print("Response Status Code:", response.status_code)
    print("Response Text:", response.text)
    return response.json()

def get_clients(query):
    url = "https://www.schedulista.com/clients/clients_json"
    payload = {
            "q":query
            }

    response = requests.get(url, headers=headers, data=payload)
    print(f"Request for {url}\n","Response Status Code:", response.status_code)
    print("Response Text:", response.text)
    return list(response.json())

def get_activities():
    url = "https://www.schedulista.com/home/fetch_activities_json?page_size=5&page=2"
    payload = {
            "page_size":"5",
            "page":"1"
            }

    response = requests.get(url, headers=headers, data=payload)
    print(f"Request for {url}\n","Response Status Code:", response.status_code)



# get_clients("yohans")
# get_activities()
# cancel_appointments()
# reschedule()
# create_client("yohans yifru","+15235698214","dee@gmail.com")
# book(1082988709)
