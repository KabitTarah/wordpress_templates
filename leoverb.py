# Distributed under MIT license (see license.txt), Copyright Tarah Z. Tamayo
#

import sys
import requests
import unicodedata
import re
import json
import dbm

DATABASE = "/home/ec2-user/git/wordpress_templates/data/verb.dbm"

TENSE_HEADERS = [
        "Indikativ",
        "Konjunktiv",
        "Imperativ",
        "Unpersönliche Zeiten"]
TENSES = [
        "Präsens",
        "Perfekt",
        "Präteritum",
        "Plusquamperfekt",
        "Futur I",
        "Futur II",
        "Konjunktiv I - Perfekt",
        "Konjunktiv II - Präteritum",
        "Konjunktiv II - Plusquamperfekt",
        "Konjunktiv I/II - Futur I"
        "Konjunktiv I/II - Futur II",
        "Präsens",
        "Partizip Präsens",
        "Partizip Perfekt"]
EN_TENSE_HEADERS = [
        "Indicative",
        "Conditional",
        "Imperative",
        "Impersonal"]
EN_TENSES = [
        "Simple present",
        "Present progressive",
        "Simple past",
        "Past progressive",
        "Present perfect",
        "Present perfect progressive",
        "Past perfect",
        "Past perfect progressive",
        "Future (will)",
        "Future (be going to)",
        "Future progressive (will)",
        "Future progressive (be going to)",
        "Future perfect",
        "Future perfect progressive",
        "Simple",
        "Progressive",
        "Perfect",
        "Perfect progressive",
        "Present",
        "Present participle",
        "Past tense",
        "Past participle"]

class LeoVerb:
    """
    Class LeoVerb - Queries dict.leo.org for verb info. Caches information to a local database for speed and to minimize
                    network traffic.
    
    Methods:
        LeoVerb(verb, interactive=True) - Constructor
        template_vars(tense_header, tense) - outputs dictionary for template filling
    """
    html = None
    html_verb_rows = None

    verb = None
    english = None
    table_link = ""
    table_key = ""
    info_leo = ""
    conjugations = None
    en_table_link = None
    en_table_key = None
    en_conjugations = None
    db_json = None
    db = None
    
    def __init__(self, verb, interactive=True):
        self.verb = verb
        self.conjugations = {}
        self._open_db()
        if self._check_db():
            self._get_db()
        else:
            self.get_trans()
            self.get_table("de")
            self.get_table("en")
        self._update_db()
        self._close_db()
        
    def _open_db(self):
        self.db = dbm.open(DATABASE, 'c')
    def _close_db(self):
        self.db.close()
    def _check_db(self) -> bool:
        if self.verb.encode('UTF-8') in self.db.keys():
            return True
        else:
            return False
    def _update_db(self):
        db = {}
        db['html'] = self.html
        db['html_verb_rows'] = self.html_verb_rows
        db['conjugations'] = self.conjugations
        db['table_link'] = self.table_link
        db['table_key'] = self.table_key
        db['info_leo'] = self.info_leo
        db['english'] = self.english
        db['en_table_link'] = self.en_table_link
        db['en_table_key'] = self.en_table_key
        db['en_conjugations'] = self.en_conjugations
        self.db_json = json.dumps(db)
        self.db[self.verb] = self.db_json
    def _get_db(self):
        db = json.loads(self.db.get(self.verb).decode('UTF-8'))
        if "html" in db.keys() and "html_verb_rows" in db.keys():
            self.html = db['html']
            self.html_verb_rows = db['html_verb_rows']
        else:
            self.get_verb_search()
            self.get_verb_section()
            self.get_verb_rows()

        if "english" in db.keys():
            self.english = db['english']
        else:
            self.get_english_trans()

        if "table_link" in db.keys() and "table_key" in db.keys():
            self.table_link = db['table_link']
            self.table_key = db['table_key']
        else:
            self.get_german_conj_link()

        if "en_table_link" in db.keys() and "en_table_key" in db.keys():
            self.en_table_link = db['en_table_link']
            self.en_table_key = db['en_table_key']
        else:
            self.get_english_conj_link()

        if "info_leo" in db.keys():
            self.info_leo = db['info_leo']
        else:
            self.get_info_link()

        if "conjugations" in db.keys():
            self.conjugations = db['conjugations']
        else:
            self.get_table("de")

        if "en_conjugations" in db.keys():
            self.en_conjugations = db['en_conjugations']
        else:
            self.get_table("en")
    
    def _sanitize_text(self, txt) -> str:
        """
        _sanitize_text(txt) - Returns the string with all unicode control characters removed (e.g. zero width spaces)
        """
        return ''.join([c for c in txt if unicodedata.category(c)[0]!="C"])

    def template_vars(self, tense_header: str, tense: str) -> dict:
        """
        template_vars(tense_header, tense) -> dict
        Inputs:
            tense_header - one of the values in leoverb.TENSE_HEADERS.
            tense        - one of the values in leoverb.TENSES
        Output:
            dictionary containing no hierarchy with special values:
                verb_de  - The requested German verb
                verb_en  - English translations of this verb (semicolon separated)
                verb_leo - The dict.leo.org dictionary key to enable links / lookups to full inflection tables
                info_leo - The dict.leo.org informational key to enable links to information / forum posts
                conj_... - Conjugations of the verb for the requested tense. These keys include the subject pronoun
                           (in place of "..." here)
        """
        if tense_header not in TENSE_HEADERS:
            raise Exception(f"Tense Header not found. Must be in { TENSE_HEADERS }.")
        if tense not in TENSES:
            raise Exception(f"Tense not found. Must be in { TENSES }.")
        t_vars = {}
        t_vars['verb_en'] = '; '.join(self.english)
        t_vars['verb_de'] = self.verb
        t_vars['verb_leo'] = self.table_key
        t_vars['info_leo'] = self.info_leo
        conj = self.conjugations[tense_header][tense]
        for key in conj.keys():
            tkey = "conj_" + key.split('/')[0]
            t_vars[tkey] = conj[key]
        return t_vars

    def get_verb_search(self):
        """
        get_verb_search() - fills self.html with the search page request. This helps us reuse the doc across many functions
        """
        # Get HTML search page for verb requested
        verb_search = self._sanitize_text(requests.get("https://dict.leo.org/german-english/" + self.verb).text)
        self.html = verb_search
    
    def get_verb_section(self):
        """
        get_verb_section() - Transforms self.html to focus on just the verb section of the search page
        """
        # A. Get table sections (Nouns, Verbs, etc) and key by section title
        section_dic = {}
        re_sec = re.compile(f'(<thead>(((?!<thead>).)*))')
        re_row = re.compile(f'(<tr>(((?!</tr>).)*)</tr>)')
        sections = re_sec.findall(self.html)
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
            raise Exception(f"No verb section for verb { self.verb }")
        else:
            self.html = section_dic['Verbs']
    
    def get_verb_rows(self):
        """
        get_verb_rows() - transforms self.html into a list of regex matches for verb dictionary entry rows
        """
        # need parens around the entire regex because we're using findall
        #regex = re.compile(f'(<tr(((?!>).)*)>(((?!</tr>).)*)data-dz-flex-label-1="{ verb }( \([0-9]+\))?"(((?!</tr>).)*)</tr>)')
        regex = re.compile(f'(<tr(((?!>).)*)data-dz-ui="dictentry"(((?!>).)*)>(((?!</tr>).)*)</tr>)')
        # use findall to find all matches even though we're *probably* interested in the 1st one
        rows = regex.findall(self.html)
        if len(rows) == 0:
            raise Exception("Verb dictionary entries not found on dict.leo.org!")
        else:
            self.html_verb_rows = rows
    
    def get_english_trans(self, interactive=True):
        # Get English translations
        if interactive:
            i = 0
            trans_cell = None
            self.english = []
            while not trans_cell and i < len(self.html_verb_rows):
                # Looking for English translations - it's the first cell with /german-english (and we pull from these) but more
                # definitively it has:
                #     <td data-dz-attr="relink" lang="en">
                # telling us this cell relinks to english words
                trans_cell = re.search(r'<td data-dz-attr="relink" lang="en">(((?!</td>).)*)</td>', self.html_verb_rows[i][0])
            
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
                    self.english.append(trans)
                    print(f"English translation now: { self.english }")
                    trans_cell = None
                if answer.upper() == "N":
                    trans_cell = None
                i += 1
            if len(self.english) == 0:
                raise Exception(f"No English chosen for { self.verb }")

    def get_german_conj_link(self):
        """
        get_german_conj_link() - Retrieves the first link to the German conjugation table
        """
        # Get conjugation page
        regex = re.compile(f'<td(((?!>).)*)>(((?!</td>).)*)data-dz-flex-label-1="{ self.verb }( \([0-9]+\))?"(((?!</td>).)*)"Open verb table"(((?!</td>).)*)</td>')
        i = 0
        conj_cell = None
        while not conj_cell and i < len(self.html_verb_rows):
            # Looking for conjugation tables (DE)
            if conj_cell is None:
                conj_cell = regex.search(self.html_verb_rows[i][0])
            if conj_cell:
                # this gets the link & verb table:
                link = re.search(r'<a href="(((?!").)*)"', conj_cell.group())
                self.table_link = "https://dict.leo.org" + link.groups()[0]
                key = re.search(r'data-dz-flex-table-1="(((?!").)*)"', conj_cell.group())
                self.table_key = key.groups()[0]
            i+=1
    
    def get_english_conj_link(self):
        """
        get_english_conj_link() - Retrieves the first link to the English conjugation table
        """
        # First English verb w/o "to"
        en_verb = self.english[0].split()[1].lower()
        
        # Get conjugation page
        regex = re.compile(f'<td(((?!>).)*)>(((?!</td>).)*)data-dz-flex-label-1="{ en_verb }( \([1-9]+\))?"(((?!</td>).)*)"Open verb table"(((?!</td>).)*)</td>')
        i = 0
        conj_cell = None
        while not conj_cell and i < len(self.html_verb_rows):
            # Looking for conjugation tables (EN)
            if conj_cell is None:
                conj_cell = regex.search(self.html_verb_rows[i][0])
            if conj_cell:
                link = re.search(r'<a href="(((?!").)*)"', conj_cell.group())
                self.en_table_link = "https://dict.leo.org" + link.groups()[0]
                key= re.search(r'data-dz-flex-table-1="(((?!").)*)"', conj_cell.group())
                self.en_table_key = key.groups()[0]
            i+=1

    def get_info_link(self):
        # Get Info page
        i = 0
        info_cell = None
        while not info_cell and i < len(self.html_verb_rows):
            info_cell = None
            info_cell = re.search(r'<td(((?!>).)*)>(((?!</td>).)*)data-dz-rel-aiid=(((?!</td>).)*)</td>', self.html_verb_rows[i][0])
            i += 1
        if not info_cell:
            print("Information page not found on leo!")
            exit()
        info_key = re.search(r'data-dz-rel-aiid="(((?!").)*)"', info_cell.group())
        self.info_leo = info_key.groups()[0]

    def get_trans(self, interactive=True):
        """
        get_trans(interative: bool=True) -
            This needs to be broken up more:
                * Grab the html document
                * Get the important bits in separate methods
                * Save html doc for posterity >.>
        """
        self.get_verb_search()

        # General steps below:
        # A. Get sections. These are identified by <thead> (separate tables on dict.leo)
        self.get_verb_section()
        # B. From the Verbs section, get all rows
        self.get_verb_rows()
        # C. Step through each row to get the info we need. Ask the user at each step
        #    User input is needed because multiple english translations exist for some verbs and different conjugation tables exist
        #    (though present tense is the same on all seen so far)
        self.get_english_trans(interactive)
        self.get_german_conj_link()
        self.get_english_conj_link()
        self.get_info_link()    
    
    def get_table(self, lang):
        if lang == "en":
            self.en_conjugations = {}
            tense_headers = EN_TENSE_HEADERS
            tenses = EN_TENSES
        else:
            self.conjugations = {}
            tense_headers = TENSE_HEADERS
            tenses = TENSES
        header = {'User-Agent': "Mozilla/5.0 (iPad; CPU OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/87.0.4280.77 Mobile/15E148 Safari/604.1"}
        if lang == "en":
            response = requests.get(self.en_table_link, headers=header)
        else:
            response = requests.get(self.table_link, headers=header)
        # RegEx to grab all rows and all columns in each row using re.findall
        conj = response.text
        conj = conj.replace('<200b>','') # Remove zero width spaces if they exist
        conj = conj.replace('\u200b','') # Remove zero width spaces if they exist
        conj_tab = []
        rows_expr = re.compile("(<tr(((?!>).)*)>(((?!</tr>).)*)</tr>)")
        head_expr = re.compile("(<th(((?!>).)*)>(((?!<th>).)*)</th>)")
        cols_expr = re.compile("(<td(((?!>).)*)>(((?!</td>).)*)</td>)")
        strip_expr = re.compile("<[^>]+>")
        rows = rows_expr.findall(conj)
        for row in rows:
            row_text = row[0]
            cols =  cols_expr.findall(row_text)
            if len(cols) == 0:
                cols = head_expr.findall(row_text)
            row_tab = ""
            for col in cols:
                row_tab = strip_expr.sub('', col[0].lstrip().rstrip())
            if row_tab:
                conj_tab.append(row_tab)

        header = ""
        tense = ""
        head_dict = {}
        tense_dict = {}
        for row in filter(lambda r: "#Search" not in r, conj_tab):
            if row in tense_headers:
                if header:
                    if lang == "en":
                        self.en_conjugations[header] = head_dict
                    else:
                        self.conjugations[header] = head_dict
                header = row
                head_dict = {}
                if tense:
                    head_dict[tense] = tense_dict
                tense = ""
                tense_dict = {}
            elif row in tenses:
                if tense:
                    head_dict[tense] = tense_dict
                tense = row
                tense_dict = {}
            else:
                row_parts = row.split()
                print(row_parts)
                if len(row_parts) > 1:
                    tense_dict[row_parts[0]] = ' '.join(row_parts[1:])
                else:
                    tense_dict = row_parts[0]
        head_dict[tense] = tense_dict
        if lang == "en":
            self.en_conjugations[header] = head_dict
        else:
            self.conjugations[header] = head_dict
    
    

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        exit()
    verb_in = sys.argv[1]
    verb = LeoVerb(verb_in)
    print("DEUTSCH")
    print(json.dumps(verb.conjugations, indent = 4))
    print("\n\nENGLISH")
    print(json.dumps(verb.en_conjugations, indent = 4))