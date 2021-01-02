import json
import requests
import jinja2
import sys
import re

# Arguments:
#   $1 german verb

if len(sys.argv) == 1:
    print("No arguments given. Please supply a verb (Deutsch)")
    exit()

verb = ' '.join(sys.argv[1:])
t_vars = {"verb_de": verb}
print(f"German verb: { verb }")

oauth_file = "/home/pi/.secrets/wp_oauth.json"
site_file = "/home/pi/.secrets/wp_site.json"

payload = json.loads(open(oauth_file).read())
site_info = json.loads(open(site_file).read())

site = site_info["site"]
template_id = site_info["template"]

oauth_url = "https://public-api.wordpress.com/oauth2/token"
api_url = "https://public-api.wordpress.com/rest/v1.1"

payload["grant_type"] = "password"
oauth_req = requests.post(oauth_url, data=payload)
oauth_resp = json.loads(oauth_req.text)
header = {"Authorization": "Bearer " + oauth_resp["access_token"]}

api = "/sites/" + site + "/posts/" + template_id
url = api_url + api

wp_req = requests.get(url, headers=header)
wp_resp = json.loads(wp_req.text)

template = jinja2.Environment(loader=jinja2.BaseLoader).from_string(wp_resp["content"])

# Get HTML search page for verb requested
verb_search = requests.get("https://dict.leo.org/german-english/" + verb).text

# Goals:
# 1. Find 1st entry (table row <tr ...>) for the verb requested
# --- <tr>...data-dz-flex-label-1="<verb>( \([0-9]+\))?"...</tr>
#
# 2. Find table cell with conj table link
#
# 3. Find table cell with info link
#
# 4. Find english translation

### 1. Get table rows:
# need parens around the entire regex because we're using findall
regex = re.compile(f'(<tr(((?!>).)*)>(((?!</tr>).)*)data-dz-flex-label-1="{ verb }( \([0-9]+\))?"(((?!</tr>).)*)</tr>)')
# use findall to find all matches even though we're *probably* interested in the 1st one
rows = regex.findall(verb_search)
if len(rows) == 0:
    print("Verb not found on dict.leo.org!")
    exit()


### 2. Find table cell with conj table link
###    and 3. Find table cell with info link
###    and 4. Find table cell with translation info
conj_cell = None
info_cell = None
trans_cell = None
i = 0
while not conj_cell and not info_cell and not trans_cell and i < len(rows):
    # We want these to come from the same row
    conj_cell = None
    info_cell = None
    trans_cell = None
    # conjugation cell:
    regex = re.compile(f'<td(((?!>).)*)>(((?!</td>).)*)data-dz-flex-label-1="{ verb }( \([0-9]+\))?"(((?!</td>).)*)"Open verb table"(((?!</td>).)*)</td>')
    conj_cell = regex.search(rows[i][0])
    info_cell = re.search(r'<td(((?!>).)*)>(((?!</td>).)*)data-dz-rel-aiid=(((?!</td>).)*)</td>', rows[i][0])
    trans_cell = re.search(r'<td(((?!>).)*)>(((?!</td>).)*)<a href="/german-english/(((?!</td>).)*)</td>', rows[i][0])
    i += 1
if not conj_cell or not info_cell or not trans_cell:
    print("Verb info not found on dict.leo.org!")
    exit()
# this gets the link & verb table:
link = re.search(r'<a href="(((?!").)*)"', conj_cell.group())
table = requests.get("https://dict.leo.org" + link.groups()[0]).text

# this gets the table key (to link to from our template)
key = re.search(r'data-dz-flex-table-1="(((?!").)*)"', conj_cell.group())
t_vars["verb_leo"] = key.groups()[0]


### 3. Find table cell with info link
# <td><a aria-label="Additional information" href="/pages/addinfo/addInfo.php?aiid=Dev5odCDopP&amp;lp=ende&amp;lang=en"><i role="img " title="Additional information" alt="i" class="icon noselect icon_information-outline icon_size_18 darkgray "><dz-data data-dz-ui="dictentry:showInfobox" data-dz-rel-aiid="Dev5odCDopP" data-dz-sprite="false"/> </i></a></td>
info_key = re.search(r'data-dz-rel-aiid="(((?!").)*)"', info_cell.group())
t_vars["info_leo"] = info_key.groups()[0]

### 4. Find translation info

trans_match = re.findall(r'/german-english/([a-zA-z-]+)', trans_cell.group())
t_vars["verb_en"] = ' '.join(trans_match)

# Find verb conjugations (present tense only)

# <span> ich</span><span> h<span class="pink">abe</span></span>

leo_pronouns = {"ich": "<span> ich</span>",
                "du": "<span> du</span>",
                "er": '<span title="Singular Maskulin"> er</span><span title="Singular Feminin">/​sie</span><span title="Singular Neutrum">/​es</span>',
                "wir": "<span> wir</span>",
                "ihr": "<span> ihr</span>",
                "sie": "<span> sie</span>"}
pronouns = {}

for pronoun in leo_pronouns.keys():
    regex = re.compile(f'{ leo_pronouns[pronoun] }<span> ([a-z]+)<span class="pink">([a-z]+)</span></span>')
    match = regex.search(table)
    if match:
        # Luckily present tense comes first
        t_vars["conj_" + pronoun] = ''.join(list(match.groups()))
title = f"{ t_vars['verb_de'] } \u2014 { t_vars['verb_en'] }"

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
wp_req = requests.post(url, headers=header, data=new_post)
print(wp_req)
wp_resp = json.loads(wp_req.text)
print(json.dumps(wp_resp, indent=4))

