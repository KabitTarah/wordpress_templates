# 
# AnkiDeVotD - Goals for this class:
#     X Get full list of verbs from wordpress -- WPT library will handle this
#     X Figure out which week we're in (based on number of verbs posts / verb list)
#     * Get the latest DeVotD yearly and weekly decks
#     * Figure out the latest verb available in DeVotD anki deck
#     * Update decks for all verbs since latest available
#     * Update media for new cards from Forvo library (to be created)
#     * Update decks on Google Drive
# 
# Distributed under MIT license (see license.txt), Copyright Tarah Z. Tamayo
#

import os
import json
from wpt import WPT
import anki
from anki.exporting import AnkiPackageExporter
from anki.importing.apkg import AnkiPackageImporter
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

class AnkiDeVotD:
    """
    AnkiDeVotD - Class to build Deutsch Verb of the Week decks and cards in Anki and deploy anki card
                 packages (weekly and yearly) for distribution.
    """
    colln_fname = "data/current/collection.anki2"
    collection = None
    decks = None   # Dictionary based on deck ID values dictionaries containing:
                   #     name - Deck name
                   #     cards - List of card IDs
    
    cwd = None
    wpt = None
    
    verb_list = None
    weeks = None
    gdrive = None
    current_pkg = None
    
    def __init__(self, wpt: object):
        self.decks = {}
        self.cwd = os.getcwd()
        self.verb_list = []
        self.weeks = []
        self.wpt = wpt
        self._get_verb_posts()
        self._build_verb_weeks()
        self.gdrive = GDrive()
        
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
            i = self.verb_list.index()
            if i < smallest_index:
                smallest_index = i
        for verb in self.verb_list[smallest_index:]
            if verb in self.missing_verbs:
                self.add_verb(verb)
    
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
    
    def get_verbs(self):
        # Cycle through all decks that fit the criteria
        for key in self.decks.keys():
            d = self.decks[key]
            if d['name'] != "default" and "Present" not in d['name']:
                for cid in d['cards']:
                    d['verbs'].add(self.get_card_verb(cid))

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
        
    def add_verb(self, verb):
        """
        add_verb(verb) - Adds the verb and its conjugations, along with any pronunciations, to the anki collection
                       - Creates new decks as needed (weekly decks)
        """
        # This method has a lot of work to do, but it's all one component. This will be an entry point for
        # votd as well.
        #
        # 1. Find next verb position (which week is the verb in?)
        # 2. Get the correct deck and sub-deck (Weekly & Present tense)
        #    a. Create these decks if they are not already formed
        #    b. Update the decks dictionary, regardless of decks prior states
        # 3. Call Forvo API to grab pronunciation (if not already in media store)
        # 4. Add pronunciation to media store
        # 5. Create notes and add to proper decks
        #
        pass

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
    print(advd.verb_list)
    
    