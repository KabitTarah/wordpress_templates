# Secrets retrieval 
#   Returns a dictionary of secrets based on application. Secrets stored in AWS SSM Parameter Store
# 
# Distributed under MIT license (see license.txt), Copyright Tarah Z. Tamayo
#

import boto3

TYPES = [
    "ssm"
]

class Secrets:
    type = ""
    ssm = None
    ssm_wp_key = "/keys/wp/"
    ssm_wp_site = "/site/"
   
    def __init__(self, type: str = "ssm", **kwargs):
        if type not in TYPES:
            raise Exception(f"Type must be one of { TYPES }")
        self.type = type
        if type == "ssm":
            if "region" not in kwargs.keys():
                raise Exception(f"AWS Region required for SSM stored secrets. Set `region='us-east-2'")
            self.ssm = boto3.client('ssm', region_name=kwargs['region'])
    
    def get_wp_key(self) -> dict:
        """
        get_wp_key() - returns dictionary of wordpress API credentials from secrets storage.
                     - defers to secrets storage routines based on storage type
        """
        if self.type == "ssm":
            return self.get_wp_key_ssm()
    
    def get_wp_key_ssm(self) -> dict:
        wp_ssm = self.ssm.get_parameters_by_path(Path=self.ssm_wp_key, WithDecryption=True)['Parameters']
        wp = {}
        for parameter in wp_ssm:
            name = parameter['Name'].split('/')[3]
            wp[name] = parameter['Value']
        wp['client_id'] = int(wp['client_id'])
        return wp
        
    def get_wp_site(self) -> dict:
        """
        get_wp_site() - returns dictionary of wordpress Site and Template information from secrets storage.
                      - defers to secrets storage routines based on storage type
        """
        if self.type == "ssm":
            return self.get_wp_site_ssm()
    
    def get_wp_site_ssm(self) -> dict:
        site_ssm = self.ssm.get_parameters_by_path(Path=self.ssm_wp_site, WithDecryption=True)['Parameters']
        site_info = {}
        for parameter in site_ssm:
            name = parameter['Name'].split('/')[2]
            site_info[name] = parameter['Value']
        return site_info
        