from pathlib import Path
from cachetools import LRUCache

class ResourceManager:
    def __init__(self, cache_size=100, location_interface_map={}):
        self.location_interface_map = location_interface_map
        self.cache = LRUCache(maxsize=cache_size)

    def get(self, path):
        path = Path(path)
        effective_path = self.get_effective_path(path)
        print(effective_path)

        # Check if the value is in cache
        if effective_path in self.cache:
            print("CACHE HIT")
            return self.cache[effective_path]

        print("CACHE MISS")
        interface = self.get_interface(path)
        value = interface.read(effective_path)

        self.cache[effective_path] = value
        return value

    def set(self, path, value):
        path = Path(path)
        effective_path = self.get_effective_path(path)
        print(f"meow meow {effective_path}")
        self.cache[effective_path] = value
        interface = self.get_interface(path)
        interface.write(effective_path, value)

    def delete(self, path):
        path = Path(path)
        effective_path = self.get_effective_path(path)

        if effective_path in self.cache:
            self.cache.pop(effective_path)
        interface = self.get_interface(path)
        interface.delete(effective_path)

    def get_interface(self, path):
        specified_location = path.parts[0]
        return self.location_interface_map[specified_location]

    def get_effective_path(self, path):
        base_path = Path(path.parts[0])
        return Path(path).relative_to(base_path)
