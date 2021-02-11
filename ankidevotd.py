# 
# AnkiDeVotD - Goals for this class:
#     * Get full list of verbs from wordpress -- WPT library will handle this
#     * Figure out which week we're in (based on number of verbs posts / verb list)
#     * Get the latest DeVotD yearly and weekly decks
#     * Figure out the latest verb available in DeVotD anki deck
#     * Update decks for all verbs since latest available
#     * Update media for new cards from Forvo library (to be created)
#     * Update decks on Google Drive
# 
# Distributed under MIT license (see license.txt), Copyright Tarah Z. Tamayo
#

import os
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
    collection
    cdw = None
    wpt = None
    
    verb_list = None
    weeks = None
    gdrive = None
    current_pkg = None
    
    def __init__(self, wpt: object):
        self.cwd = os.getcwd()
        self.verb_list = []
        self.weeks = []
        self.wpt = wpt
        self._get_verb_posts()
        self._build_verb_weeks()
        self.gdrive = Gdrive()
        
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
        fname = self.gdrive.dl_year((len(self.weeks) // 52) + 1)
        self.current_pkg = self.cwd + "/data/" + fname
        self.open_collection()
        self.importpkg()
    
    def open_collection(self):
        self.collection = anki.Collection(self.cwd + self.colln_fname)
        
    def importpkg(self):
        importer = AnkiPackageImporter(self.collection, self.current_pkg)
        importer.run()


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
        try:
            self._refresh_creds(self.gauth)
            self.drive = GoogleDrive(gauth)
        except:
            print("Something went wrong in Google Drive!")
        os.chdir("..")
        self.get_folder_id(self.folder)
    
    def _refresh_creds(self, gauth):
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile("drivecreds.txt")
        if gauth.credentials is None:
            gauth.CommandLineAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()
        gauth.SaveCredentialsFile("drivecreds.txt")

    def get_folder_id(self, folder):
        file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
        for f in filter(lambda f: f['title']==folder, file_list):
            self.folder_id = f['id']

    def dl_package(self, pkg_name) -> bool:
        if self.folder_id is None:
            self.get_folder_id(self.folder)
        os.chdir("data")
        file_list = self.drive.ListFile({'q': f"'{ self.folder_id }' in parents and trashed=false"}).GetList()
        for f in filter(lambda f: f['title'] == pkg_name, file_list):
            f.GetContentFile(f['title'])
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
    print(len(advd.verb_list))
    for i, week in enumerate(advd.weeks):
        print(f"{ i+1 } - { week }")
    
    
    
    