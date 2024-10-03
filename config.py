import os
from apify_client import ApifyClient


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    NUBELA_API_KEY = os.environ.get('NUBELA_API_KEY') or 'your-nubela-api-key'
    APIFY_API_KEY = os.environ.get('APIFY_API_KEY') or 'your-apify-api-key'
    APIFY_CLIENT = ApifyClient(token=os.environ.get('APIFY_API_KEY'))

    GOOGLE_DRIVE_FOLDER_ID = '13qlaX_eHBkMV60JaszK_JgqjQVhb1mVI'

    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.environ.get('REDIS_PORT') or 6379)
    REDIS_DB = int(os.environ.get('REDIS_DB') or 0)

    TINYDB_PATH = 'db.json'
