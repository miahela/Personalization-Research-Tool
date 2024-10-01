import logging
logging.basicConfig(level=logging.INFO)

from flask import Flask
from config import Config
from app.utils.file_manager import FileManager
app = Flask(__name__)
app.config.from_object(Config)
file_manager = FileManager(app)

from app import routes