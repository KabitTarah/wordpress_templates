import sys
import requests
import unicodedata
import re
import json
import dbm

DATABASE = "data/verbs.dbm"

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

class leoverb:
    verb = None
    english = None
    table_link = ""
    table_key = ""
    conjugations = None
    db_json = None
    db = None
    
    def __init__(self, verb, interactive=True):
        self.verb = verb
        self.conjugations = {}
        self._open_db()
        if self._check_db():
            self._get_db()
        else:
            self.get_trans(interactive)
            self.get_table()
            self._update_db()
        self._close_db()
        
    def _open_db(self):
        self.db = dbm.open(DATABASE, 'c')
    def _close_db(self):
        self.db.close()
    def _check_db(self) -> bool:
        print(f"Checking db contents: { list(self.db.keys()) }")
        if self.verb.encode('UTF-8') in self.db.keys():
            return True
        else:
            return False
    def _update_db(self):
        print("Outputting to DB")
        db = {}
        db['conjugations'] = self.conjugations
        db['table_link'] = self.table_link
        db['table_key'] = self.table_key
        db['english'] = self.english
        self.db_json = json.dumps(db)
        self.db[self.verb] = self.db_json
    def _get_db(self):
        db = json.loads(self.db.get(self.verb).decode('UTF-8'))
        self.conjugations = db['conjugations']
        self.table_link = db['table_link']
        self.table_key = db['table_key']
        self.english = db['english']
        print(f"Got from DB { self.verb } - { self.english }")

    def _sanitize_text(self, txt) -> str:
        # Some web data contains zero width strings and possibly other control characters. This strips them out
        return ''.join([c for c in txt if unicodedata.category(c)[0]!="C"])

    def get_trans(self, interactive=True):
        # Get HTML search page for verb requested
        verb_search = self._sanitize_text(requests.get("https://dict.leo.org/german-english/" + self.verb).text)

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
            raise Exception(f"No verb section for verb { self.verb }")
            
        ### B. Get all dictentry table rows from verbs section:
        # need parens around the entire regex because we're using findall
        #regex = re.compile(f'(<tr(((?!>).)*)>(((?!</tr>).)*)data-dz-flex-label-1="{ verb }( \([0-9]+\))?"(((?!</tr>).)*)</tr>)')
        regex = re.compile(f'(<tr(((?!>).)*)data-dz-ui="dictentry"(((?!>).)*)>(((?!</tr>).)*)</tr>)')
        # use findall to find all matches even though we're *probably* interested in the 1st one
        rows = regex.findall(section_dic['Verbs'])
        if len(rows) == 0:
            raise Exception("Verb dictionary entries not found on dict.leo.org!")

        # Get English translations
        i = 0
        trans_cell = None
        self.english = []
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
                self.english.append(trans)
                print(f"English translation now: { self.english }")
                trans_cell = None
            if answer.upper() == "N":
                trans_cell = None
            i += 1
        if len(self.english) == 0:
            raise Exception(f"No English chosen for { self.verb }")
        
        # Get conjugation page
        i = 0
        conj_cell = None
        while not conj_cell and i < len(rows):
            # Looking for conjugation tables
            regex = re.compile(f'<td(((?!>).)*)>(((?!</td>).)*)data-dz-flex-label-1="{ self.verb }( \([0-9]+\))?"(((?!</td>).)*)"Open verb table"(((?!</td>).)*)</td>')
            conj_cell = regex.search(rows[i][0])
            if conj_cell:
                # this gets the link & verb table:
                link = re.search(r'<a href="(((?!").)*)"', conj_cell.group())
                self.table_link = "https://dict.leo.org" + link.groups()[0]
                key = re.search(r'data-dz-flex-table-1="(((?!").)*)"', conj_cell.group())
                self.table_key = key.groups()[0]
            i+=1
    
    def get_table(self):
        header = {'User-Agent': "Mozilla/5.0 (iPad; CPU OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/87.0.4280.77 Mobile/15E148 Safari/604.1"}
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
            if row in TENSE_HEADERS:
                if header:
                    self.conjugations[header] = head_dict
                header = row
                head_dict = {}
                if tense:
                    head_dict[tense] = tense_dict
                tense = ""
                tense_dict = {}
            elif row in TENSES:
                if tense:
                    head_dict[tense] = tense_dict
                tense = row
                tense_dict = {}
            else:
                row_parts = row.split()
                if len(row_parts) > 1:
                    tense_dict[row_parts[0]] = ' '.join(row_parts[1:])
                else:
                    tense_dict = row_parts[0]
        head_dict[tense] = tense_dict
        self.conjugations[header] = head_dict
    
    

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        exit()
    verb_in = sys.argv[1]
    verb = leoverb(verb_in)