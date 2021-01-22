import boto3
import json
import requests

ssm = boto3.client('ssm', region_name="us-east-2")

wp_ssm = ssm.get_parameters_by_path(Path='/keys/wp/', WithDecryption=True)['Parameters']
wp = {}
for parameter in wp_ssm:
    name = parameter['Name'].split('/')[3]
    wp[name] = parameter['Value']
wp['client_id'] = int(wp['client_id'])

oauth_url = "https://public-api.wordpress.com/oauth2/token"

wp["grant_type"] = "password"
oauth_req = requests.post(oauth_url, data=wp)
oauth_resp = json.loads(oauth_req.text)
wp['access_token'] = oauth_resp['access_token']

print(wp)