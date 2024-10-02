import os
from apify_client import ApifyClient


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    NUBELA_API_KEY = os.environ.get('NUBELA_API_KEY') or 'your-nubela-api-key'
    APIFY_API_KEY = os.environ.get('APIFY_API_KEY') or 'your-apify-api-key'
    APIFY_CLIENT = ApifyClient(token=os.environ.get('APIFY_API_KEY'))
    FILE_STORAGE_PATH = 'file_storage'
    GOOGLE_DRIVE_FOLDER_ID = '13qlaX_eHBkMV60JaszK_JgqjQVhb1mVI'
