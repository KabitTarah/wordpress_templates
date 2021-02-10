import os
import json
import re
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import anki

folder = "DeVOTD"

def authorize_drive():
    gauth = GoogleAuth()
    gauth.DEFAULT_SETTINGS['client_config_file'] = "auth/client_secret.json"
    gauth.LoadCredentialsFile("auth/drivecreds.txt")
    return GoogleDrive(gauth)

class DriveReport(object):
    def __init__(self):
        self.drive = authorize_drive()

os.chdir("auth")
gauth = GoogleAuth()
gauth.LoadCredentialsFile("drivecreds.txt")
if gauth.credentials is None:
    gauth.CommandLineAuth()
elif gauth.access_token_expired:
    gauth.Refresh()
else:
    gauth.Authorize()
gauth.SaveCredentialsFile("drivecreds.txt")
os.chdir("..")

drive = GoogleDrive(gauth)
file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
for f in filter(lambda f: f['title']==folder, file_list):
    folder_id = f['id']

file_list = drive.ListFile({'q': f"'{ folder_id }' in parents and trashed=false"}).GetList()
week = 0
latest = None
for f in filter(lambda f: "Week" in f['title'] and ".apkg" in f['title'], file_list):
    match = re.search(r"Week ([0-9]+)\.apkg$", f['title'])
    if match:
        if int(match.groups()[0]) > week:
            week = int(match.groups()[0])
            latest = f

os.chdir("data")
print(f"Downloading { latest['title'] } from Google Drive")
latest.GetContentFile(latest['title'])
for f in filter(lambda f: f['title'] == "German VotD.apkg", file_list):
    print(f"Downloading { f['title'] } from Google Drive")
    f.GetContentFile(f['title'])

cwd = os.getcwd()
latest_path = cwd + latest['title']
deck = anki.Collection(latest_path)
print(deck)

os.chdir("..")
