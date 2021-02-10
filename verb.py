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

from leo.leoverb import LeoVerb

class VerbRunner:
    """
    VerbRunner(?, ?)
        Orchestrator for other moving parts. Can take in a single verb or operate against multiple gleaned verbs
    """
    
    # LeoVerb object
    current_verb = None
    # Dictionary cache of LeoVerb objects keyed on German verb
    leo_verbs = None
    
    def __init__(self):
        """
        VerbRunner() - Constructor. Empty for now.
        """
        self.leo_verbs = {}
    
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
        
