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

# !TODO! Need to search post titles for requested verb to verify it hasn't been used
url = f"https://public-api.wordpress.com/rest/v1.2/sites/{ site }/posts/?search={ verb }"
wp_req = requests.get(url, headers=auth_header)
wp_resp = json.loads(wp_req.text)
for post in wp_resp['posts']:
    title = post['title'].split('\u2014')
    if title[0].rstrip() == verb:
        print(f"ERROR: Verb already used in '{ post['title'] }'")
        print(f"  Trace URL: { post['URL'] }")
        exit(1)

# Get HTML search page for verb requested
verb_search = sanitize_text(requests.get("https://dict.leo.org/german-english/" + verb).text)

# General steps below:
# A. Get sections. These are identified by <thead> (separate tables on dict.leo)
# B. From the Verbs section, get all rows
# C. Step through each row to get the info we need. Ask the user at each step
#    User input is needed because multiple english translations exist for some verbs and different conjugation tables exist
#    (though present tense is the same on all seen so far)

# A. Get table sections (Nouns, Verbs, etc) and key by section title
section_dic = {}
re_sec = re.compile(f'(<thead>(((?!<thead>).)*))')
re_row = re.compile(f'(<tr>(((?!</tr>).)*)</tr>)')
sections = re_sec.findall(verb_search)
for section in sections:
    header = re_row.search(section[0])
    if header:
        title = re.search(r'<h2 (((?!>).)*)>(((?!<).)*)</h2>', header.group())
        # 0 = rest of header
        # 1 = last char of 0
        # 2 = title
        # 3 = last char of title
        if title:
            section_dic[title.groups()[2]] = section[0]
if 'Verbs' not in section_dic.keys():
    print(f"No verb section for verb { verb }!")
    exit()

# Special Cases:
# gehen   - "normal" case (completed)
# kommen  - two table sets have labels "kommen (1)" and "kommen (2)" (completed)
# tun     - special case in conj table - no root (all is conj extension and is in pink. Change + to * for root part)
# treffen - Nouns come first (split up sections and grabbed the Verb section - some reusable code here if I move on to other parts of speech)
#         - Multiple english translations (to meet or to hit / strike)
#         - unicode control characters in conj table (whyyy)

### B. Get all dictentry table rows from verbs section:
# need parens around the entire regex because we're using findall
#regex = re.compile(f'(<tr(((?!>).)*)>(((?!</tr>).)*)data-dz-flex-label-1="{ verb }( \([0-9]+\))?"(((?!</tr>).)*)</tr>)')
regex = re.compile(f'(<tr(((?!>).)*)data-dz-ui="dictentry"(((?!>).)*)>(((?!</tr>).)*)</tr>)')
# use findall to find all matches even though we're *probably* interested in the 1st one
rows = regex.findall(section_dic['Verbs'])
if len(rows) == 0:
    print("Verb dictionary entries not found on dict.leo.org!")
    exit()

# Get English translations
i = 0
trans_cell = None
t_vars["verb_en"] = ""
while not trans_cell and i < len(rows):
    # Looking for English translations - it's the first cell with /german-english (and we pull from these) but more
    # definitively it has:
    #     <td data-dz-attr="relink" lang="en">
    # telling us this cell relinks to english words
    trans_cell = re.search(r'<td data-dz-attr="relink" lang="en">(((?!</td>).)*)</td>', rows[i][0])

    ### Find translation info
    trans_match = re.findall(r'/german-english/([a-zA-z-]+)', trans_cell.group())
    trans = ' '.join(trans_match)
    print(f"English translation found: { trans }")
    answer = ""
    while answer.upper() not in ["Y", "N", "Q"]:
        print("Add / Quit (Y/n/Q)?")
        answer = sys.stdin.read(1)
        sys.stdin.readline()
    if answer.upper() == "Y":
        if len(t_vars["verb_en"]) > 0:
            t_vars["verb_en"] += "; "
        t_vars["verb_en"] += trans
        print(f"English translation now: { t_vars['verb_en'] }")
        trans_cell = None
    if answer.upper() == "N":
        trans_cell = None
    i += 1

leo_pronouns = {"ich": "<span> ich</span>",
                "du": "<span> du</span>",
                "er": '<span title="Singular Maskulin"> er</span><span title="Singular Feminin">/sie</span><span title="Singular Neutrum">/es</span>',
                "wir": "<span> wir</span>",
                "ihr": "<span> ihr</span>",
                "sie": "<span> sie</span>"}
title = f"{ t_vars['verb_de'] } \u2014 { t_vars['verb_en'] }"

# Get conjugations
i = 0
conj_cell = None
while not conj_cell and i < len(rows):
    # Looking for conjugation tables
    regex = re.compile(f'<td(((?!>).)*)>(((?!</td>).)*)data-dz-flex-label-1="{ verb }( \([0-9]+\))?"(((?!</td>).)*)"Open verb table"(((?!</td>).)*)</td>')
    conj_cell = regex.search(rows[i][0])
    if conj_cell:
        # this gets the link & verb table:
        link = re.search(r'<a href="(((?!").)*)"', conj_cell.group())
        table = sanitize_text(requests.get("https://dict.leo.org" + link.groups()[0]).text)
        print(f"https://dict.leo.org{ link.groups()[0] }")
        table = table.replace('<200b>','') # Remove zero width spaces if they exist
        # this gets the table key (to link to from our template)
        key = re.search(r'data-dz-flex-table-1="(((?!").)*)"', conj_cell.group())
        t_vars["verb_leo"] = key.groups()[0]

        print()
        print('Conjugation:')
        for pronoun in leo_pronouns.keys():
            regex = re.compile(f'{ leo_pronouns[pronoun] }<span> (\w*)<span class="pink">(\w+)</span></span>')
            match = regex.search(table)
            if match:
                # Luckily present tense comes first
                t_vars["conj_" + pronoun] = ''.join(list(match.groups()))
            else:
                t_vars["conj_" + pronoun] = ""
            print(f'{ pronoun }: { t_vars["conj_" + pronoun] }')
        answer = ""
        while answer.upper() not in ["Y", "N"]:
            print("Conj OK? (Y/n)")
            answer = sys.stdin.read(1)
            sys.stdin.readline()
            if answer.upper() == "N":
                conj_cell = None
    i += 1

# Get Info page
i = 0
info_cell = None
while not info_cell and i < len(rows):
    info_cell = None
    info_cell = re.search(r'<td(((?!>).)*)>(((?!</td>).)*)data-dz-rel-aiid=(((?!</td>).)*)</td>', rows[i][0])
    i += 1
if not info_cell:
    print("Information page not found on leo!")
    exit()
info_key = re.search(r'data-dz-rel-aiid="(((?!").)*)"', info_cell.group())
t_vars["info_leo"] = info_key.groups()[0]

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

