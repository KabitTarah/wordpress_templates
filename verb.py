# 
# Verb runner - This is the core class for this project to orchestrate work performed
#    - Intended to be run from CLI with entry points based on CLI arguments
#    - Intended to be flexible, able to be invoked
# 
# General Workflow:
#    - Verb of the Day chosen by user
#    - Verb looked up using leo library
#    - Verb published to Wordpress.com
#    - Media downloaded via Forvo API (pay-for service $2/mo non-commercial)
#    - Anki decks updated for:
#        (a) current week - Defined by a package of 7 verbs, not defined by calendar day
#        (b) current year - Overall packages per calendar year (1st year anything prior to Jan 1 2022)
#                         - Yearly packages should all have the same main folder (German VotD)
#    - Anki decks uploaded to Google Drive for distribution 
#
# Distributed under MIT license (see license.txt), Copyright Tarah Z. Tamayo
#

import sys
from leoverb import LeoVerb
from wpt import WPT

class VerbRunner:
    """
    VerbRunner(?, ?)
        Orchestrator for other moving parts. Can take in a single verb or operate against multiple gleaned verbs
    """
    # Wordpress object
    wpt = None
    # LeoVerb object
    current_verb = None
    # Dictionary cache of LeoVerb objects keyed on German verb
    leo_verbs = None
    
    def __init__(self):
        """
        VerbRunner() - Constructor. Empty for now.
        """
        self.leo_verbs = {}
        self._set_wpt()
    
    def _set_wpt(self):
        self.wpt = WPT(secret_store="ssm", region="us-east-2")
    
    def _save_current(self, leo_verb):
        """
        self._save_current(leo_verb) - Private method to update current leo_verb and update cache
        """
        self.current_verb = leo_verb
        self.leo_verbs[leo_verb.verb] = leo_verb
    
    def votd(self, verb: str):
        """
        VerbRunner.votd(verb)
          - Runs an interactive session to generate and post the verb of the day. Saves a LeoVerb object into
            current_verb
        """
        leo_verb = LeoVerb(verb)
        self._save_current(leo_verb)
        found_post = self.wpt.find_title_keyword(verb)
        if found_post is not None:
            print(f"Verb { verb } already used in post { found_post['title'] }")
            print(f"   Traceback URL: { found_post['URL'] }")
            exit(1)
        template_vars = leo_verb.template_vars("Indikativ", "Präsens")
        self.wpt.set_template_vars(template_vars)
        title = self.wpt.get_title()
        print(f"Title: { title }")
        print()
        for key in template_vars.keys():
            print(f"{ key }: { template_vars[key] }")
        print()
        answer = ""
        while answer.upper() not in ["Y", "N"]:
            print("Ok? (Y/n)")
            answer = sys.stdin.read(1)

        if answer.upper() == "N":
            print("Ok, exiting.")
            exit()
        
        self.wpt.post(["Verbs"], ["Indikativ", "Präsens"])

# CLI arguments and number of total arguments required (must be at least 1)
CLI = {
    "votd": 2
}
     
if __name__ == "__main__":
    vr = VerbRunner()
    if len(sys.argv) < 2:
        print(f"At least one keyword argument is required from:")
        for arg in CLI.keys():
            print(f"    { arg }")
        exit(1)
    if sys.argv[1] not in CLI.keys():
        print(f"Only the following keywords are permitted:")
        for arg in CLI.keys():
            print(f"    { arg }")
        exit(1)
    if len(sys.argv) != CLI[sys.argv[1]] + 1:
        print(f"Argument { sys.argv[1] } requires { CLI[sys.argv[1]] - 1 } additional arguments.")
        exit(1)
    if sys.argv[1] == "votd":
        verb = sys.argv[2]
        vr.votd(verb)