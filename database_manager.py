import json
from PIL import Image
import io
import base64

class DatabaseManager:
    def __init__(self):
        pass

    def read_json(self, file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Error: The file at {file_path} was not found.")
        except json.JSONDecodeError:
            print(f"Error: The file at {file_path} does not contain valid JSON.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def write_json(self, file_path, data):
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            print(f"An error occurred while writing to {file_path}: {e}")

    def read_image(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                img_data = file.read()
            # Encode image data to base64 directly
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            return img_base64
        except FileNotFoundError:
            print(f"Error: The file at {file_path} was not found.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def write_image(self, file_path, img_base64):
        try:
            # Decode base64 to binary image data directly
            img_data = base64.b64decode(img_base64)
            with open(file_path, 'wb') as file:
                file.write(img_data)
        except Exception as e:
            print(f"An error occurred while writing to {file_path}: {e}")

