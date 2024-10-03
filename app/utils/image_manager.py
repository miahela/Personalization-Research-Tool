# app/utils/image_manager.py

import os
import requests
import logging
from glob import glob
from mimetypes import guess_extension
from werkzeug.utils import secure_filename
from flask import current_app
from typing import Optional


class ImageManager:
    _instance = None

    def __init__(self):
        self.image_storage_path = os.path.join(current_app.static_folder, 'images')
        self._ensure_storage_directory()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_storage_directory(self):
        os.makedirs(self.image_storage_path, exist_ok=True)

    def get_or_download_image(self, image_url: Optional[str], username: str, image_type: str) -> Optional[str]:
        """
        Get an existing image or download and save a new one.

        :param image_url: URL of the image to download
        :param username: Unique identifier for the contact (e.g., LinkedIn username)
        :param image_type: Type of the image (e.g., 'profile', 'banner')
        :return: The URL path to access the saved image, or None if failed
        """
        if not image_url:
            return None

        existing_image = self.get_image_url(f'{username}_{image_type}')
        if existing_image:
            return existing_image

        # If no existing file, download the image
        response = requests.get(image_url)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').split(';')[0]
            ext = guess_extension(content_type)

            if not ext:
                logging.warning(
                    f"Couldn't determine file extension for {image_type} image of {username}. Defaulting to .jpg")
                ext = '.jpg'

            filename = f'{username}_{image_type}{ext}'
            return self.save_image(response.content, filename)
        else:
            logging.error(f"Failed to download {image_type} image for {username}")
            return None

    def save_image(self, image_content: bytes, filename: str) -> str:
        """
        Save an image file associated with a contact.

        :param image_content: The binary content of the image
        :param filename: Filename of the image
        :return: The URL path to access the saved image
        """
        secure_name = secure_filename(filename)
        file_path = os.path.join(self.image_storage_path, secure_name)

        with open(file_path, 'wb') as f:
            f.write(image_content)

        return f'/static/images/{secure_name}'

    def delete_images_by_contact(self, username: str):
        """
        Delete all images associated with a specific contact.

        :param username: Unique identifier for the contact (e.g., LinkedIn username)
        """
        pattern = os.path.join(self.image_storage_path, f"{username}*")
        for file_path in glob(pattern):
            os.remove(file_path)

    def get_image_url(self, filename_pattern: str) -> Optional[str]:
        """
        Get the URL of an image based on a filename pattern.

        :param filename_pattern: Pattern to match the filename
        :return: The URL path to access the image, or None if not found
        """
        pattern = os.path.join(self.image_storage_path, filename_pattern)
        existing_files = glob(pattern)
        if existing_files:
            return f'/static/images/{os.path.basename(existing_files[0])}'
        return None
