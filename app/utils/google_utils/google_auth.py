import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import orjson

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]


class GoogleService:
    _instance = None

    def __init__(self):
        self.creds = None
        self.services = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._get_credentials()

    def _get_credentials(self):
        if os.path.exists('token.json'):
            try:
                self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            except orjson.JSONDecodeError:
                os.remove('token.json')

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = Flow.from_client_secrets_file(
                    'client_secrets.json', SCOPES)
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

                auth_url, _ = flow.authorization_url(prompt='consent')

                print(f'Please go to this URL and authorize the application: {auth_url}')
                code = input('Enter the authorization code: ')

                flow.fetch_token(code=code)
                self.creds = flow.credentials

            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

    def get_service(self, service_name, version):
        if service_name not in self.services:
            self.services[service_name] = build(service_name, version, credentials=self.creds)
        return self.services[service_name]
