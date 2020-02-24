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
            # TODO fixme
            self.cache.update({key: value})

    def pop(self, key):
        if key in self.cache:
            return self.cache.pop(key)
        return None

    def get(self, item):
        return self._cache.get(item)

    def exists(self, key):
        return key in self._cache

    def clear(self):
        self._cache = {}


class PypadsRunCache(Cache):
    def __init__(self, run):
        super().__init__()
        self._run = run or mlflow.active_run()
        if not self._run:
            raise ValueError("No active run for run cache found.")

    @property
    def run(self):
        return self._run


class PypadsCache(Cache):

    def __init__(self):
        super().__init__()
        self._run_caches = {}

    def run_init(self, run_id=None):
        if run_id is None:
            run = mlflow.active_run()
        else:
            run = mlflow.get_run(run_id)
        if not run:
            raise ValueError("No run is active. Couldn't init run cache.")
        if run not in self._run_caches:
            self._run_caches[run] = PypadsRunCache(run)
        return run

    def run_add(self, key, value, run_id=None):
        run = self.run_init(run_id)
        self._run_caches[run].add(key, value)

    def run_pop(self, key, run_id=None):
        run = self.run_init(run_id)
        return self._run_caches[run].prop(key)

    def run_get(self, key, run_id=None):
        run = self.run_init(run_id)
        return self._run_caches[run].get(key)

    def run_exists(self, key, run_id=None):
        run = self.run_init(run_id)
        return self._run_caches[run].exists(key)

    def run_clear(self, run_id=None):
        run = self.run_init(run_id)
        self._run_caches[run].clear()
