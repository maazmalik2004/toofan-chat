import collections

class CacheManager:
    def __init__(self, max_length, load_callback, store_callback):
        self.max_length = max_length
        self.cache = collections.OrderedDict()
        self.load_callback = load_callback
        self.store_callback = store_callback

    def get_length(self):
        return len(self.cache)

    def activate(self, key, value):
        # If the key is already in the cache, eat 5 star, do nothing
        if key in self.cache:
            print(f'{key} ALREADY ACTIVE')
            return
        
        # Eviction logic: pop the LRU item if cache is full. before popping store the context
        if len(self.cache) == self.max_length:
            evicted_key, evicted_value = self.cache.popitem(last=False)
            self.store_callback(evicted_key, evicted_value)
            print(f'{evicted_key} EVICTED')

        self.cache[key] = value
        print(f'{key} ACTIVATED')

    def deactivate(self, key):
        if key in self.cache:
            value = self.cache.pop(key)
            self.store_callback(key, value)
            print(f'{key} DEACTIVATED')
        else:
            print(f'{key} ALREADY DEACTIVE')

    def get(self, key):
        print(self.cache)
        if key in self.cache:
            value = self.cache.pop(key)
            self.cache[key] = value
            print(f'{key} FOUND IN CACHE')
            return value
        else:
            value = self.load_callback(key)
            if value is None:
                print(f'{key} NOT FOUND IN SECONDARY STORE (LIKE DB)')
                return None

            self.activate(key, value)
            return value
            
    def update(self, key, value):
        if key in self.cache:
            self.cache[key] = value
            self.cache.move_to_end(key)
            print(f'{key} UPDATED')
        else:
            self.activate(key, value)

    def save_all(self):
        print("Saving all cache items to the database...")
        for key, value in self.cache.items():
            self.store_callback(key, value)
            print(f'{key} SAVED TO DB')
