import os
import sqlite3
from datetime import datetime
import shutil
from glob import glob

import orjson
import re
from flask import current_app


class FileManager:
    _instance = None

    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['file_manager'] = self

        self.db_path = app.config.get('FILE_MANAGER_DB_PATH', 'file_metadata.db')
        self.file_storage_path = app.config.get('FILE_STORAGE_PATH', 'file_storage')
        self.image_storage_path = os.path.join(app.static_folder, 'images')

        self._ensure_storage_directories()
        self._init_db()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_url TEXT,
                    file_type TEXT NOT NULL,
                    user_id TEXT,
                    is_frontend_image BOOLEAN NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def _ensure_storage_directories(self):
        os.makedirs(self.file_storage_path, exist_ok=True)
        os.makedirs(self.image_storage_path, exist_ok=True)

    def save_file(self, file_content, filename, file_type, user_id, is_frontend_image=False):
        if is_frontend_image:
            file_path = os.path.join(self.image_storage_path, filename)
            with open(file_path, 'wb') as f:
                f.write(file_content)
        else:
            file_path = os.path.join(self.file_storage_path, filename)
            with open(file_path, 'wb') as f:
                f.write(orjson.dumps(file_content))

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO files (filename, file_type, user_id, is_frontend_image)
                VALUES (?, ?, ?, ?)
            ''', (filename, file_type, user_id, is_frontend_image))
            conn.commit()

        return file_path

    def get_file_path(self, filename):
        # Check if it's a frontend image
        image_path = os.path.join(self.image_storage_path, filename)
        if os.path.exists(image_path):
            return image_path

        # If not, check in the regular file storage
        return os.path.join(self.file_storage_path, filename)

    def get_file_metadata(self, filename):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE filename = ?', (filename,))
            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'filename': result[1],
                    'original_url': result[2],
                    'file_type': result[3],
                    'user_id': result[4],
                    'is_frontend_image': result[5],
                    'created_at': result[6]
                }
            return None

    def delete_file(self, filename):
        file_path = self.get_file_path(filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM files WHERE filename = ?', (filename,))
            conn.commit()

    def get_files_by_user(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT filename, file_type, is_frontend_image FROM files WHERE user_id = ?', (user_id,))
            return cursor.fetchall()

    def delete_all_files_by_user(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT filename FROM files WHERE user_id = ?', (user_id,))
            files = cursor.fetchall()
            for file in files:
                self.delete_file(file[0])

    def get_frontend_image_url(self, filename):
        existing_files = glob(os.path.join(self.image_storage_path, filename))
        if existing_files:
            return f'/static/images/{os.path.basename(existing_files[0])}'
        return None

    def load_json_file(self, filename):
        file_path = os.path.join(self.file_storage_path, filename)
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'rb') as f:
            return orjson.loads(f.read())


def get_file_manager():
    if 'file_manager' not in current_app.extensions:
        return FileManager.get_instance()
    return current_app.extensions['file_manager']
