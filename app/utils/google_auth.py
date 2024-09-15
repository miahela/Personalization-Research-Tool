import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import json

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except json.JSONDecodeError:
            os.remove('token.json')
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = Flow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print(f'Please go to this URL and authorize the application: {auth_url}')
            code = input('Enter the authorization code: ')
            
            flow.fetch_token(code=code)
            creds = flow.credentials
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds