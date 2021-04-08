
class CacheManager(object):
    def __init__(self):
        self.key_value_cache = {}
        self.hash_cache = {}

    def get(self, key):
        self.key_value_cache.get(key)

    def set(self, key, value):
        self.key_value_cache[key] = value

    def hget(self, hash, key):
        return self.hash_cache.get(name, {}).get(key)

    def hset(self, hash, key, value):
        if not hash in self.hash_cache:
            self.hash_cache[hash] = {}
        self.hash_cache[hash][key] = value

    def hclear(self, hash, key=None):
        if key:
            self.hash_cache.get(hash, {}).pop(key, None)
        else:
            self.hash_cache[hash] = {}

    def hexists(self, hash):
        return bool(self.hash_cache.get(hash))