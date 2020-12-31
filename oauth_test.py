import json
import requests

secrets_file = "/home/pi/.secrets/secrets.json"

oauth_url = "https://public-api.wordpress.com/oauth2/token"
with open(secrets_file) as f:
    payload = json.loads(f.read())

if "access_token" in payload.keys():
    print("Access token already created. Please remove to retrieve new token.")
else:
    payload["grant_type"] = "password"
    oauth_req = requests.post(oauth_url, data=payload)
    oauth_resp = json.loads(oauth_req.text)
    payload['access_token'] = oauth_resp['access_token']
    with open(secrets_file, 'w') as f:
        f.write(json.dumps(payload, indent=4))
