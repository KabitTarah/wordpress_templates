# 
# Forvo API
#   A class to automate the download of a pronunciation using the Forvo API. The top rated pronunciation is 
#   retrieved. Duplicates are avoided. A filename / path is returned.
#
# Secrets are retrieved from AWS SSM Parameter Store abstracted in secrets.py
# 
# Distributed under MIT license (see license.txt), Copyright Tarah Z. Tamayo
# 

import os
import requests
import json
from secrets import Secrets

class Forvo:
    """
    """
    
    data_dir = "data/forvo/"
    secrets = None
    api_key = None
    api_url = "https://apifree.forvo.com/key"
    
    def __init__(self, secret_store: str="ssm", **kwargs):
        self.secrets = Secrets(type=secret_store, **kwargs)
    
    def _get_secrets(self):
        self.api_key = self.secrets.get_forvo_key()
    
    def get_pronunciation(self, word: str) -> str:
        if self.api_key is None:
            self._get_secrets()
        
        fname = f"{ os.getcwd() }/{ self.data_dir }/{ word }.mp3"
        if os.path.exists(fname):
            return fname
        
        api = f"format/json/action/word-pronunciations/word/{ word }/language/de/country/DEU/order/rate-desc/limit/1"
        url = f"{ self.api_url }/{ self.api_key }/{ api }"
        
        req = requests.get(url)
        data = json.loads(req.text)['items'][0]
        print(json.dumps(data, indent=4))
        # we care about data['pathmp3']
        mp3 = requests.get(data['pathmp3'])
        with open(fname, 'wb') as fp:
            fp.write(mp3.content)
        return fname
        
        
if __name__ == "__main__":
    forvo = Forvo(secret_store="ssm", region="us-east-2")
    forvo.get_pronunciation("dürfen")
    
    
    
    
    
    
    
    
    
    
    