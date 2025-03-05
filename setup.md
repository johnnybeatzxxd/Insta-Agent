## Generating Access Token
Visit the following address replacing the client ID and the redirect URI:
https://api.instagram.com/oauth/authorize/?client_id=[clientID]&redirect_uri=[redirectURI]&response_type=code

# code will be returned in url param or send via webhook
use that code and request for access token
curl -F 'client_id=[clientID]' -F 'client_secret=[clientSecret]' -F 'grant_type=authorization_code' -F 'redirect_uri=[redirectURI]' -F 'code=[code]' https://api.instagram.com/oauth/access_token
Copy the access token from the returned JSON object.

# Generate long lived access token
use this code to generate long lived access token
```
    url = "https://graph.instagram.com/access_token"
    params = {
        "grant_type": "ig_exchange_token",
        "client_secret": config["app_secret"],
        "access_token": short_lived_token
    }
    print(params)
    # Make the GET request
    try:
        response = requests.get(url, params=params)
        
        # Log response details
        print(f"Response Status Code: {response.status_code}")
        
        try:
            print(f"Response Body: {response.json()}")
        except requests.exceptions.JSONDecodeError:
            print(f"Failed to decode JSON response. Raw response: {response.text}")
            
        # Check if request was successful
        response.raise_for_status()
        return response
        
    except requests.exceptions.RequestException as e:
        print(f"Error getting long-lived token: {str(e)}")
        return None

```
replace the params with the correct creds

