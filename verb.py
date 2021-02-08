class leoverb:
    verb = None

    def __init__(self, verb, interactive=True):
        self.verb = verb
        self.verb_lookup(interactive)

    def verb_lookup(interactive=True):
        # Get HTML search page for verb requested
        verb_search = sanitize_text(requests.get("https://dict.leo.org/german-english/" + self.verb).text)

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
            raise Exception(f"No verb section for verb { verb }")
