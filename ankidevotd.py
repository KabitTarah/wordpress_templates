# 
# AnkiDeVotD - Goals for this class:
#     X Get full list of verbs from wordpress -- WPT library will handle this
#     X Figure out which week we're in (based on number of verbs posts / verb list)
#     X Get the latest DeVotD yearly deck
#     X Figure out the latest verb available in DeVotD anki deck
#     * Update media for new cards from Forvo library
#     * Update decks for all verbs since latest available
#     * Update decks on Google Drive
# 
# Distributed under MIT license (see license.txt), Copyright Tarah Z. Tamayo
#

import os
import json
from wpt import WPT
from leoverb import LeoVerb
from forvo import Forvo
import anki
from anki.exporting import AnkiPackageExporter
from anki.importing.apkg import AnkiPackageImporter
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# German --> English **field** translations
FIELD_TRANSLATION_TABLE = {
    "Indikativ": "Indicative",
    "Präsens": "Simple present",
    "ich": "I",
    "du": "you",
    "er/sie/es": "he/she/it",
    "wir": "we",
    "ihr": "you",
    "sie": "they"}

# German --> English **NOTE** translations
PRONOUN_TRANSLATION_TABLE = {
    "ich": "I",
    "du": "you (informal)",
    "er/sie/es": "he/she/they/it",
    "wir": "we",
    "ihr": "you (plural, informal)",
    "sie": "you (formal) / they"}

# German --> German **NOTE** translations
PRONOUN_NOTE_TABLE = {
    "ich": "ich",
    "du": "du",
    "er/sie/es": "er / sie / es",
    "wir": "wir",
    "ihr": "ihr", 
    "sie": "Sie / sie"}

class AnkiDeVotD:
    """
    AnkiDeVotD - Class to build Deutsch Verb of the Week decks and cards in Anki and deploy anki card
                 packages (weekly and yearly) for distribution.
    """
    colln_fname = "data/current/collection.anki2"
    collection = None
    decks = None   # Dictionary based on deck ID values dictionaries containing:
                   #     name  - Deck name
                   #     cards - List of card IDs
                   #     verbs - set of verbs used in this deck (for weekly root decks)
    week_decks = None  # decks indexed by week
    
    # These are all tenses currently included in deck building, plus the infinitive
    tenses = {
        "Present": [["Indikativ", "Präsens"], ["Indicative", "Simple present"]]
    }
    
    cwd = None
    data_dir = "data"
    full_output_file = "German VotD.apkg"
    wpt = None
    
    verb_list = None
    weeks = None
    gdrive = None
    forvo = None
    current_pkg = None
    
    def __init__(self, wpt: object):
        self.decks = {}
        self.week_decks = {}
        self.cwd = os.getcwd()
        self.verb_list = []
        self.weeks = []
        self.wpt = wpt
        self._get_verb_posts()
        self._build_verb_weeks()
        self.gdrive = GDrive()
        self.forvo = Forvo("ssm", region="us-east-2")
        
    def _get_verb_posts(self):
        titles = self.wpt.get_titles("Verbs")
        self.verb_list = [title.split("\u2014")[0].strip() for title in titles]
    
    def _build_verb_weeks(self):
        week = []
        for verb in self.verb_list:
            week.append(verb)
            if len(week) == 7:
                self.weeks.append(week)
                week = []
        if len(week) > 0:
            self.weeks.append(week)
    
    def run(self):
        """
        run() - Workflow to update all verbs not yet created in Anki collection.
        """
        fname = self.gdrive.dl_year((len(self.weeks) // 52) + 1)
        self.current_pkg = self.cwd + "/data/" + fname
        self.open_collection()
        self.importpkg()
        self.get_decks()
        self.get_verbs()
        
        # We care about order - the self.verb_list is in posted order and they should be added in this order
        smallest_index = len(self.verb_list)
        missing_verbs = self.get_missing_verbs()
        for verb in missing_verbs:
            i = self.verb_list.index(verb)
            if i < smallest_index:
                smallest_index = i
        for verb in self.verb_list[smallest_index:]:
            if verb in missing_verbs:
                self.add_verb(verb)
        
        self.package_full()

        self.collection.close()
    
    def open_collection(self):
        self.collection = anki.Collection('/'.join([self.cwd, self.colln_fname]))
        
    def importpkg(self):
        importer = AnkiPackageImporter(self.collection, self.current_pkg)
        importer.run()
    
    def get_decks(self):
        """
        get_decks() - Gets all decks in the collection and assigns them to the deck dictionary
        """
        decks = self.collection.decks.all_names_and_ids()
        for deck in decks:                
            print(f"{deck.id} - {deck.name}")
            self.decks[deck.id] = {
                "name":  deck.name,
                "cards": self.collection.decks.cids(deck.id),
                "verbs": set()
            }
            # This section is specific to how I set up my decks. Keyed by week, there should be at least
            # 2 deck IDs per week, stored in a list
            name_parts = deck.name.split("::")
            if len(name_parts) == 1:
                week = 0
            else:
                week = int(name_parts[1].split()[1])
                if week not in self.week_decks.keys():
                    self.week_decks[week] = []
                self.week_decks[week].append(deck.id)
    
    def get_verbs(self):
        # Cycle through all decks that fit the criteria
        for key in self.decks.keys():
            d = self.decks[key]
            if d['name'] != "default" and "Present" not in d['name']:
                for cid in d['cards']:
                    d['verbs'].add(self.get_card_verb(cid))
                print(f"{ d['name'] } - { d['verbs'] }")

    def get_card_verb(self, cid: int) -> str:
        """
        get_card_verb(cid) - Gets the verb from the note on the card specified by the card ID (cid)
        """
        card = self.collection.getCard(cid)
        note = self.collection.getNote(card.nid)
        # field 1 is the card back
        verb = note.fields[1].split('<')[0]
        return verb
    
    def get_missing_verbs(self) -> list:
        """
        get_missing_verbs() - Returns a list of all verbs not found in the current anki project
        """
        present_verbs = set()
        for key in self.decks.keys():
            d = self.decks[key]
            present_verbs = present_verbs.union(d['verbs'])
        print(present_verbs)
        all_verbs = set(self.verb_list)
        print(all_verbs.difference(present_verbs))
        return all_verbs.difference(present_verbs)
    
    def get_next_verb_deck(self) -> dict:
        """
        get_next_verb_deck() - Looks through the decks list for the latest week. If there are fewer than 7
                               verbs, the deck is returned. If there are 7 verbs, kicks off creation of new
                               decks.
        """
        week = len(self.week_decks.keys())
        week_decks = self.week_decks[week]
        decks = {}
        if len(self.decks[week_decks[0]]['verbs']):
            decks['Infinitive'] = week_decks[0]
            decks['Present'] = week_decks[1]
        else:
            decks['Infinitive'] = week_decks[1]
            decks['Present'] = week_decks[0]
        if len(self.decks[decks['Infinitive']]['verbs']) == 7:
            week += 1
            decks = self.create_new_weekly_deck(week)
        return decks
    
    def create_new_weekly_deck(self, week: int) -> list:
        decks = {}
        self.week_decks[week] = []
        base_name = f"German VotD::Week { week }"
        decks['Infinitive'] = self.collection.decks.id(base_name)
        self.week_decks[week].append(decks['Infinitive'])
        self.decks[decks['Infinitive']] = {
                "name":  base_name,
                "cards": self.collection.decks.cids(decks['Infinitive']),
                "verbs": set()
            }
        tense_names = []
        for tense in self.tenses.keys():
            tense_name = f"German VotD::Week { week }::{ tense }"
            decks[tense] = self.collection.decks.id(tense_name)
            self.week_decks[week].append(decks[tense])
            self.decks[decks[tense]] = {
                    "name":  tense_name,
                    "cards": self.collection.decks.cids(decks[tense]),
                    "verbs": set()
                }
        return decks
    
    def get_media_link(self, word) -> str:
        """
        get_media_link(word) - gets the media link if in the media manager or initiates grab + add
        """
        media_link = f"<div>[sound:{ word }.mp3]</div>"
        # Default forvo (library) filenames for words are f"{ word }.mp3
        if self.collection.media.have(f"{ word }.mp3"):
            return media_link
        media_path = self.forvo.get_pronunciation(word)
        if media_path is not None:
            self.collection.media.add_file(media_path)
            return media_link
        else:
            return ""

    def get_model(self, tense):
        """
        get_model(tense) - Gets an Anki model based on tense
        """
        if tense == "Infinitive":
            model_name = "Basic (and reversed card)"
        else:
            model_name = "Basic"
        return self.collection.models.get(self.collection.models.id_for_name(model_name))

    def add_verb(self, verb):
        """
        add_verb(verb) - Adds the verb and its conjugations, along with any pronunciations, to the anki collection
                       - Creates new decks as needed (weekly decks)
        """
        # This method has a lot of work to do, but it's all one component. This will be an entry point for
        # votd as well.
        #
        # X. Find next verb position (which week is the verb in?)
        # X. Get the correct deck and sub-deck (Weekly & Present tense)
        #    X. Create these decks if they are not already formed
        #    X. Update the decks dictionary, regardless of decks prior states
        # X. Call Forvo API to grab pronunciation (if not already in media store)
        # X. Add pronunciation to media store
        # X. Create notes and add to proper decks
        #
        
        # This is how we define our note information structure:
        #    LeoVerb - This contains two dictionaries plus the german and english verb:
        #       - conjugations - German conjugation dictionary
        #       - en_conjugations - English conjugation dictionary
        #       - verb - German infinitive
        #       - english - English infinitive
        #    self.tenses - This contains a reference to the deck tense and a list for each reference:
        #       - self.tenses[tense][0] - German key hierarchy in LeoVerb.conjugations
        #       - self.tenses[tense][1] - English key hierarchy in LeoVerb.conjugations

        print(f"Adding { verb } to anki collection")
        decks = self.get_next_verb_deck()
        print("** Decks:")
        print(json.dumps(decks, indent=4))
        leo = LeoVerb(verb)
        en_inf = '; '.join(leo.english)
        media_link = self.get_media_link(leo.verb)
        notes = {      # Dictionary of list of cards with Front (english) and Back (german) - Starting with infinitive
            "Infinitive": [[en_inf, f"{ leo.verb }{ media_link }"]]
            } 
        for tense in filter(lambda t: t != "Infinitive", decks.keys()):
            tense_notes = []
            path = self.tenses[tense]
            # sets up de_conj and en_conj to be the leo conjugations for this tense
            de_conj = leo.conjugations
            for p in path[0]:
                de_conj = de_conj[p]
            en_conj = leo.en_conjugations
            for p in path[1]:
                en_conj = en_conj[p]
            # Cycle through pronouns and create notes
            for pronoun in de_conj.keys():
                de_pn = PRONOUN_NOTE_TABLE[pronoun]
                en_f = FIELD_TRANSLATION_TABLE[pronoun]
                en_pn = PRONOUN_TRANSLATION_TABLE[pronoun]
                media_link = self.get_media_link(de_conj[pronoun])
                note_txt = [f"{ en_pn } { en_conj[en_f] }<br>({ en_inf })", f"{ de_pn } { de_conj[pronoun] } { media_link }"]
                tense_notes.append(note_txt)
            notes[tense] = tense_notes
        
        # CREATE CARDS!!!
        for tense in decks.keys():
            model = self.get_model(tense)
            for note_txt in notes[tense]:
                note = anki.notes.Note(self.collection, model)
                note.fields = note_txt
                self.collection.add_note(note, decks[tense])
            if tense == "Infinitive":
                self.decks[decks[tense]]['verbs'].add(leo.verb)

    def package_full(self):
        output_file = '/'.join([self.cwd, self.data_dir, self.full_output_file])
        exporter = AnkiPackageExporter(self.collection)
        exporter.exportInto(output_file)

def authorize_drive():
    gauth = GoogleAuth()
    gauth.DEFAULT_SETTINGS['client_config_file'] = "client_secret.json"
    gauth.LoadCredentialsFile("drivecreds.txt")
    return GoogleDrive(gauth)

class DriveReport(object):
    def __init__(self):
        self.drive = authorize_drive()

class GDrive:
    """
    class GDrive - Trying to keep this as simple as possible to enable grabbing files as needed and sending new 
                   packages to drive
    """
    folder = "DeVOTD"
    gauth = None
    drive = None
    folder_id = None
    
    def __init__(self):
        os.chdir("auth")
        self._refresh_creds()
        self.drive = GoogleDrive(self.gauth)
        os.chdir("..")
        self.get_folder_id(self.folder)
    
    def _refresh_creds(self):
        self.gauth = GoogleAuth()
        self.gauth.LoadCredentialsFile("drivecreds.txt")
        if self.gauth.credentials is None:
            self.gauth.CommandLineAuth()
        elif self.gauth.access_token_expired:
            self.gauth.Refresh()
        else:
            self.gauth.Authorize()
        self.gauth.SaveCredentialsFile("drivecreds.txt")

    def get_folder_id(self, folder):
        file_list = self.drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
        for f in filter(lambda f: f['title']==folder, file_list):
            self.folder_id = f['id']

    def dl_package(self, pkg_name) -> bool:
        """
        dl_package(pkg_name) -  Downloads Google Drive package if the remote version is newer than the local version
        """
        if self.folder_id is None:
            self.get_folder_id(self.folder)
        os.chdir("data")
        file_list = self.drive.ListFile({'q': f"'{ self.folder_id }' in parents and trashed=false"}).GetList()
        # Save the meta info - Only download if the revision is larger
        if os.path.exists(f"{ pkg_name }.meta"):
            with open(f"{ pkg_name }.meta") as metafile:
                meta = json.load(metafile)
        else:
            meta = {"version": "0"}
        # Get the file that matches the pkg_name - there should only be one
        for f in filter(lambda f: f['title'] == pkg_name, file_list):
            # Check the version from the disk version (if disk version exists)
            if int(meta['version']) < int(f['version']):
                print(f"Downloading { f['title'] }")
                f.GetContentFile(f['title'])
                with open(f"{ pkg_name }.meta", "w") as metafile:
                    json.dump(f, metafile)
        os.chdir("..")
        return True

    # Sorry - this is not modularized yet and is specific to this project
    def dl_week(self, week) -> str:
        fname = f"German VotD__Week { week }.apkg"
        if self.dl_package(fname):
            return fname
        else:
            return None
    
    # Sorry - this is not modularized yet and is specific to this project
    def dl_year(self, year):
        if year == 1:
            fname = f"German VotD.apkg"
        else:
            fname = f"German VotD { year }.apkg"
        if self.dl_package(fname):
            return fname
        else:
            return None

if __name__ == "__main__":
    wpt = WPT("ssm", region="us-east-2")
    advd = AnkiDeVotD(wpt)
    advd.run()
