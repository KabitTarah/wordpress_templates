# Distributed under MIT license (see license.txt), Copyright Tarah Z. Tamayo
#

import leoverb
import boto3
import json
import requests
import jinja2
import sys
import re
import unicodedata

def sanitize_text(txt) -> str:
    # Some web data contains zero width strings and possibly other control characters. This strips them out
    return ''.join([c for c in txt if unicodedata.category(c)[0]!="C"])

# Constants
ssm = boto3.client('ssm', region_name="us-east-2")
wp_path = "/keys/wp/"
site_path = "/site/"

# Get WP parameters
wp_ssm = ssm.get_parameters_by_path(Path=wp_path, WithDecryption=True)['Parameters']
wp = {}
for parameter in wp_ssm:
    name = parameter['Name'].split('/')[3]
    wp[name] = parameter['Value']
wp['client_id'] = int(wp['client_id'])

# Get Site parameters
site_ssm = ssm.get_parameters_by_path(Path=site_path, WithDecryption=True)['Parameters']
site_info = {}
for parameter in site_ssm:
    name = parameter['Name'].split('/')[2]
    site_info[name] = parameter['Value']

# Arguments:
#   $1 german verb
if len(sys.argv) == 1:
    print("No arguments given. Please supply a verb (Deutsch)")
    exit()

# All CLI arguments make up the total verb
verb = ' '.join(sys.argv[1:])
# set this in the jinja replacement dictionary
t_vars = {"verb_de": verb}
print(f"German verb: { verb }")

leo = leoverb.LeoVerb(verb)
t_vars = leo.template_vars("Indikativ", "Präsens")

# Get OAUTH info from WP.com
site = site_info["url"]
template_id = site_info["template"]

oauth_url = "https://public-api.wordpress.com/oauth2/token"
api_url = "https://public-api.wordpress.com/rest/v1.1"

wp["grant_type"] = "password"
oauth_req = requests.post(oauth_url, data=wp)
oauth_resp = json.loads(oauth_req.text)
auth_header = {"Authorization": "Bearer " + oauth_resp["access_token"]}

# Get the template post (usually private). This post should be in Jinja2 formatted HTML
api = "/sites/" + site + "/posts/" + template_id
url = api_url + api
wp_req = requests.get(url, headers=auth_header)
wp_resp = json.loads(wp_req.text)
# This sets up the template object within the jinja2 framework
template = jinja2.Environment(loader=jinja2.BaseLoader).from_string(wp_resp["content"])

url = f"https://public-api.wordpress.com/rest/v1.2/sites/{ site }/posts/?search={ verb }"
wp_req = requests.get(url, headers=auth_header)
wp_resp = json.loads(wp_req.text)
for post in wp_resp['posts']:
    title = post['title'].split('\u2014')
    if title[0].rstrip() == verb:
        print(f"ERROR: Verb already used in '{ post['title'] }'")
        print(f"  Trace URL: { post['URL'] }")
        exit(1)

title = f"{ t_vars['verb_de'] } \u2014 { t_vars['verb_en'] }"

print()
print(json.dumps(t_vars, indent=4))
print()
print(f"Title: { title }")
print()
answer = ""
while answer.upper() not in ["Y", "N"]:
    print("Ok? (Y/n)")
    answer = sys.stdin.read(1)

if answer.upper() == "N":
    print("Ok, exiting.")
    exit()

# Now we can finally fill out the template!
new_post = {}
new_post["content"] = template.render(t_vars)
new_post["title"] = title
new_post["categories"] = "Verbs"

api = "/sites/" + site + "/posts/new/" 
url = api_url + api
print(url)
wp_req = requests.post(url, headers=auth_header, data=new_post)
print(wp_req)
wp_resp = json.loads(wp_req.text)
print(json.dumps(wp_resp, indent=4))

