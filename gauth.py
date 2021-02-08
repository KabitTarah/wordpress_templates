import os
import json
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

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
for f in file_list:
    print(json.dumps(f, indent=4))
