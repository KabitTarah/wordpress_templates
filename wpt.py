# 
# Word Press Templating
#   A class to automate the retrieval, fill-in, and post/publish of a private wordpress.com Jinja2
#   template (stored as unpublished blog post)
#
# Secrets are retrieved from AWS SSM Parameter Store abstracted in secrets.py
# 
# Distributed under MIT license (see license.txt), Copyright Tarah Z. Tamayo
# 

from secrets import Secrets
import json
import requests
import jinja2

class WPT:
    secrets = None
    wp_key = None
    wp_site = None
    wp_oauth_header = None
    wp_template_title = None
    wp_template_body = None
    template_vars = None
    post_response = None
    
    oauth_url = "https://public-api.wordpress.com/oauth2/token"
    api_url = "https://public-api.wordpress.com/rest/v1.1"
    
    def __init__(self, secret_store: str="ssm", **kwargs):        
        self.secrets = Secrets(secret_store, **kwargs)
    
    def _get_secrets(self):
        self.wp_key = self.secrets.get_wp_key()
    def _get_site(self):
        self.wp_site = self.secrets.get_wp_site()
    def _wp_authorize(self):
        if self.wp_key is None:
            self._get_secrets()
        self.wp_key['grant_type'] = "password"
        oauth_req = requests.post(self.oauth_url, data=self.wp_key)
        oauth_resp = json.loads(oauth_req.text)
        self.wp_oauth_header = {"Authorization": "Bearer " + oauth_resp["access_token"]}
    
    def get_template(self):
        if self.wp_key is None:
            self._get_secrets()
        if self.wp_site is None:
            self._get_site()
        if self.wp_oauth_header is None:
            self._wp_authorize()
        
        site = self.wp_site['url']
        template_id = self.wp_site['template']

        # Get the template post (usually private). This post should be in Jinja2 formatted HTML
        api = "/sites/" + site + "/posts/" + template_id
        url = self.api_url + api
        wp_req = requests.get(url, headers=self.wp_oauth_header)
        wp_resp = json.loads(wp_req.text)
        self.set_template(wp_resp['title'], wp_resp['content'])
 
    def set_template(self, title_template: str, body_template: str):
        """
        set_template(title_template, body_template)
          - Sets the template variables. This can be used in place of get_template() for customized template
            changes.
        """
        # This sets up the template objects within the jinja2 framework
        self.wp_template_title = jinja2.Environment(loader=jinja2.BaseLoader).from_string(title_template))
        self.wp_template_body = jinja2.Environment(loader=jinja2.BaseLoader).from_string(body_template)
    
    def find_title_keyword(self, title_keyword: str) -> bool:
        """
        find_title_keyword(title_keyword) -> bool
          - Determines whether the keyword has already been used in a post title. This is to avoid duplicates
            assuming a unique keyword used. (This project has a unique verb string)
            (note that this may not be entirely unique in the case of compound or prefixed verbs)
        """
        site = self.wp_site['url']
        url = f"https://public-api.wordpress.com/rest/v1.2/sites/{ site }/posts/?search={ title_keyword }"
        wp_req = requests.get(url, headers=self.wp_oauth_header)
        wp_resp = json.loads(wp_req.text)
        for post in wp_resp['posts']:
            title = post['title'].split('\u2014')  # This splits on em-dash; need a way to make this more generic
            if title[0].rstrip() == verb:
                return True
                # raise Exception(f"ERROR: Duplicate word used in '{ post['title'] }'\n  Trace URL: { post['URL'] }")
        return False
    
    def set_template_vars(self, template_vars: dict):
        """
        set_template_vars(template_vars) - Assigns the template vars dictionary to the wordpress templating engine
        """

    def get_title(self) -> str:
        """
        get_title() - Fills in the Title template and returns it as a string
        """
        if self.template_vars is None:
            raise Exception(f"Use set_template_vars first before filling in template.")
        return self.wp_template_title.render(self.template_vars)
    
    def get_body(self) -> str:
        """
        get_body(template_vars) - Fills in the Body template and returns it as a string
        """
        if self.template_vars is None:
            raise Exception(f"Use set_template_vars first before filling in template.")
        return self.wp_template_body.render(self.template_vars)
    
    def post(self, categories: list=[], tags: list=[]) -> str:
        """
        post() - Fills in templates and creates new WordPress post
        """
        new_post = {}
        new_post['content'] = self.get_body()
        new_post['title'] = self.get_title()
        new_post['categories'] = categories
        new_post['tags'] = tags
        
        site = self.wp_site['url']
        api = "/sites/" + site + "/posts/new/"
        url = api_url + api
        wp_req = requests.post(url, headers=auth_header, data=new_post)
        self.post_response = json.loads(wp_req.text)
