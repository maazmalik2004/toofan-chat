import json
import os
from pathlib import Path

class ChatHistoryInterface:
    def __init__(self, filename='chat_history.json'):
        self._filename = filename
        self._dictionary = self._load_dictionary()

    def _load_dictionary(self):
        if os.path.exists(self._filename):
            with open(self._filename, 'r') as file:
                return json.load(file)
        return {}

    def _save_dictionary(self):
        with open(self._filename, 'w') as file:
            json.dump(self._dictionary, file)

    def read(self, key):
        # Convert the key (Path) to string before using it
        key = str(key)
        print(f"Reading key: {key}, Type: {type(key)}")
        return self._dictionary.get(key)

    def write(self, key, value):
        # Convert the key (Path) to string before using it
        key = str(key)
        print(f"Writing key: {key}, Type: {type(key)}, Value: {value}")
        self._dictionary[key] = value
        self._save_dictionary()

    def delete(self, key):
        # Convert the key (Path) to string before using it
        key = str(key)
        print(f"Deleting key: {key}")
        del self._dictionary[key]
        self._save_dictionary()
