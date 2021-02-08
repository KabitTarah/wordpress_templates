# wordpress_templates
Filling in template posts to generate new posts in WordPress

wp_oauth.json requires:
* client_id = provided by developer.wordpress.com/apps
* client_secret = provided by developer.wordpress.com/apps
* username = WP Username
* password = WP Password
* grant_type = "password"

I'm still not sure how to generate valid OAuth connection from CLI for a WP App

wp_site.json requires:
* site = site URL or site ID#
* template = template post ID

This code is all specific to my use case at https://de.kabit.club

# template_verb.py

Requires a german verb as its only argument. Looks up english translation and verb present tense conjugations on dict.leo.org and gets URL info to fill out the wordpress template specified (private or public post in a WP domain you control). Also verifies whether the verb already exists (may need updates for compound verbs with one part already included or vice versa)

# ganki.py

Initial work with google authentication and Anki decks. Changes to subdirectory `auth/` (excluded in .gitignore). This directory must contain a client_secrets.json file pointing to a Google Drive API Application. Credential tokens are also saved in this directory. Credentials use remote code verification to allow interactive authorization from an ec2 instance.

Downloads the latest anki deck and the full collection into the `data/` directory (excluded in .gitignore).

# Next steps

Automatically generate an anki deck for these items. The deck should have card GUIDs that are stable, so regenerating the deck does not duplicate / destroy card history. Anki deck to be stored in this repo or at https://de.kabit.club
