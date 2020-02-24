import mlflow


class Cache:
    def __init__(self):
        self._cache = {}

    @property
    def cache(self):
        return self._cache

    def add(self, key, value):
        if key in self.cache:
            self.cache.get(key).update(value)
        else:
            self.cache.update({key: value})

    def pop(self, key):
        if key in self.cache:
            return self.cache.pop(key)
        return None

    def get(self, item):
        return self._cache.get(item)

    def clear(self):
        self._cache = {}


class PypadsRunCache(Cache):
    def __init__(self):
        super().__init__()
        self._run = mlflow.active_run()
        if self._run:
            raise ValueError("No active run for run cache found.")

    @property
    def run(self):
        return self._run


class PypadsCache(Cache):

    def __init__(self):
        super().__init__()
        self._run_caches = {}

    def run_init(self):
        active_run = mlflow.active_run()
        if not active_run:
            raise ValueError("No run is active. Couldn't init run cache.")
        if active_run not in self._run_caches:
            self._run_caches[active_run] = PypadsRunCache()
        return active_run

    def run_add(self, key, value):
        active_run = self.run_init()
        self._run_caches[active_run].add(key, value)

    def run_pop(self, key):
        active_run = self.run_init()
        self._run_caches[active_run].prop(key)

    def run_get(self, key):
        active_run = self.run_init()
        self._run_caches[active_run].get(key)

    def run_clear(self):
        active_run = self.run_init()
        self._run_caches[active_run].clear()
