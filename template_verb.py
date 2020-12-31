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

verb_search = requests.get("https://dict.leo.org/german-english/" + verb).text
# First <tr...> with "data-dz-flex-label-1" = "haben"
#
# <tr data-dz-ui="dictentry"  data-dz-rel-uid="941200" data-dz-rel-aiid="PluTF3tcF47" class="is-clickable"><td>
# ......
# <td data-dz-attr="relink" lang="en"><samp><a href="/german-english/to">to</a> <a href="/german-english/have">have</a>  <small><i><span title="auxiliary">aux.</span></i></small>
# <a href="/pages/flecttab/flectionTable.php?kvz=4dkrADn71HeCbYCs67UP8lumz53RnXNnd4k4UOp95DaWagA5HfVNsltHXGnW64LCt7_6hM2-RVXTa5ApnoR7RM6R_uxHbjSDgu88hb2-UmZSKoC5voANxPt&amp;lp=ende&amp;lang=en"
#    data-dz-ui="dictentry:showFlecttab" data-dz-flex-table-1="4dkrADn71HeCbYCs67UP8lumz53RnXNnd4k4UOp95DaWagA5HfVNsltHXGnW64LCt7_6hM2-RVXTa5ApnoR7RM6R_uxHbjSDgu88hb2-UmZSKoC5voANxPt"
#    data-dz-flex-label-1="have" title="Open verb table" aria-label="Open verb table"><small>| had, had |</small></a></samp></td><td class="">
# <a href="/pages/flecttab/flectionTable.php?kvz=4dkrADn71HeCbYC86wUP8lumz53RnXJXdzk4UOs95DMyOsAoG5LNgyvnKX31aZKb5xiLFr7PROBkEYHPChS7kt1BX3XWvgKBERyd9S2do9LuPIW_XJE_lAqDH7xS64fVQX89IKvqIgHS_UYvboQ79KeG2Luhu_TBka6-tn4_g2HUOIcPHhNsB12CDxtwO7I0Vp--BlAA9ye&amp;lp=ende&amp;lang=en"
#    data-dz-ui="dictentry:showFlecttab" data-dz-flex-table-1="4dkrADn71HeCbYC86wUP8lumz53RnXJXdzk4UOs95DMyOsAoG5LNgyvnKX31aZKb5xiLFr7PROBkEYHPChS7kt1BX3XWvgKBERyd9S2do9LuPIW_XJE_lAqDH7xS64fVQX89IKvqIgHS_UYvboQ79KeG2Luhu_TBka6-tn4_g2HUOIcPHhNsB12CDxtwO7I0Vp--BlAA9ye"
#    data-dz-flex-label-1="haben" title="Open verb table" aria-label="Open verb table">
# <i role="img " alt="F" class="icon noselect icon_split-view-left-right icon_size_18 darkgray "> </i></a></td>
# ......
# </tr>

regex = re.compile(f'<tr(((?!(</tr>|data-dz-flex-label-1="{ verb }")).)*)<a href="(((?!").)*)" +data-dz-ui="dictentry:showFlecttab" +data-dz-flex-table-1="(((?!").)*)" +data-dz-flex-label-1="{ verb }" +title="Open verb table" +aria-label="Open verb table">')
match = regex.search(verb_search)
# Groups that should be found:
#   0: Bunch of stuff I need to look through for English translation and info link
#   1: last character in that sequence
#   2: None (the middle match that is NOT supposed to be found with the negative lookahead)
#   3: URL for verb table
#   4: last character in that sequence
#   5: URL Key for verb table (used in template)
#   6: last character in that sequence

if not match:
    print("Verb not found on dict.leo.org!")
    exit()

t_vars["verb_leo"] = match.groups()[5]
table = verb_search = requests.get("https://dict.leo.org" + match.groups()[3]).text

en_match = re.findall(r'/german-english/([a-zA-Z-]+)', match.groups()[0])
t_vars["verb_en"] = ' '.join(en_match)

info_match = re.search(r'data-dz-rel-aiid="(((?!").)*)"', match.groups()[0])
t_vars["info_leo"] = list(info_match.groups())[0]

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

