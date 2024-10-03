import unittest
import os
import orjson
from pathlib import Path
from pydantic import ValidationError
from typing import List, Dict
from app.models.nubela_response_models import NubelaResponse  # Assuming you've placed the models in this location


class TestNubelaResponseModel(unittest.TestCase):
    def setUp(self):
        # Set up the path to the user data folder
        self.user_data_folder = Path('file_storage')  # Adjust this path as needed

        print("Current working directory:", os.getcwd())
        # Print the full path to the user data folder
        print("User data folder path:", self.user_data_folder.resolve())

    def test_nubela_files(self):
        nubela_files = self._get_nubela_files()
        self.assertTrue(nubela_files, "No Nubela files found in the user data folder")

        for file_path in nubela_files:
            with self.subTest(file=file_path.name):
                try:
                    with open(file_path, 'rb') as f:
                        data = orjson.loads(f.read())

                    nubela_response = NubelaResponse.parse_obj(data)
                    self._validate_parsed_data(nubela_response, data)

                except ValidationError as e:
                    self.fail(f"Validation error in {file_path.name}: {str(e)}")
                except orjson.JSONDecodeError:
                    self.fail(f"Invalid JSON in file: {file_path.name}")
                except Exception as e:
                    self.fail(f"Unexpected error processing {file_path.name}: {str(e)}")

    def _get_nubela_files(self) -> List[Path]:
        return list(self.user_data_folder.glob("*nubela*.json"))

    def _validate_parsed_data(self, parsed: NubelaResponse, original: Dict):
        # Check if all fields in the original data are present in the parsed object
        for key, value in original.items():
            with self.subTest(field=key):
                self.assertTrue(hasattr(parsed, key), f"Field '{key}' is missing in the parsed object")
                parsed_value = getattr(parsed, key)

                if isinstance(value, dict):
                    self._validate_nested_dict(parsed_value, value, key)
                elif isinstance(value, list):
                    self._validate_nested_list(parsed_value, value, key)
                else:
                    self.assertEqual(parsed_value, value, f"Value mismatch for field '{key}'")

    def _validate_nested_dict(self, parsed_dict, original_dict, parent_key):
        for key, value in original_dict.items():
            with self.subTest(field=f"{parent_key}.{key}"):
                self.assertTrue(hasattr(parsed_dict, key),
                                f"Field '{parent_key}.{key}' is missing in the parsed object")
                parsed_value = getattr(parsed_dict, key)

                if isinstance(value, dict):
                    self._validate_nested_dict(parsed_value, value, f"{parent_key}.{key}")
                elif isinstance(value, list):
                    self._validate_nested_list(parsed_value, value, f"{parent_key}.{key}")
                else:
                    self.assertEqual(parsed_value, value, f"Value mismatch for field '{parent_key}.{key}'")

    def _validate_nested_list(self, parsed_list, original_list, parent_key):
        self.assertEqual(len(parsed_list), len(original_list), f"List length mismatch for '{parent_key}'")

        for i, (parsed_item, original_item) in enumerate(zip(parsed_list, original_list)):
            with self.subTest(item=f"{parent_key}[{i}]"):
                if isinstance(original_item, dict):
                    self._validate_nested_dict(parsed_item, original_item, f"{parent_key}[{i}]")
                elif isinstance(original_item, list):
                    self._validate_nested_list(parsed_item, original_item, f"{parent_key}[{i}]")
                else:
                    self.assertEqual(parsed_item, original_item, f"Value mismatch for item '{parent_key}[{i}]'")


if __name__ == "__main__":
    unittest.main()
