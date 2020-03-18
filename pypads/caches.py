from logging import debug

import mlflow


class Cache:
    def __init__(self):
        self._cache = {}

    @property
    def cache(self):
        return self._cache

    def add(self, key, value):
        if key in self.cache:
            if isinstance(value, dict):
                self.cache.get(key).update(value)
            else:
                self.cache[key] = value
        else:
            self.cache.update({key: value})

    def pop(self, key, default=None):
        if key in self.cache:
            return self.cache.pop(key, default)
        return None

    def get(self, item, default=None):
        return self._cache.get(item,default)

    def items(self):
        return self._cache.items()

    def exists(self, key):
        return key in self._cache

    def clear(self):
        self._cache = {}

    # def __getstate__(self):
    #     """
    #     Overwrite standard pickling by excluding the functions
    #     :return:
    #     """
    #     # TODO can't pickle functions
    #     state = self.__dict__.copy()
    #     if "cache_cleanup" in self._cache:
    #         del state["_cache"]
    #     return state
    #
    # def __setstate__(self, state):
    #     self.__dict__.update(state)
    #     if hasattr(self, "_cache") or self._cache is None:
    #         self._cache = {}


class PypadsRunCache(Cache):
    def __init__(self, run):
        super().__init__()
        self._run = run or mlflow.active_run()
        if not self._run:
            raise ValueError("No active run for run cache found.")

    @property
    def run(self):
        return self._run

    def register_cleanup_fn(self):
        from pypads.base import get_current_pads
        pads = get_current_pads()

        def cleanup_cache(run_id=self._run.info.run_id):
            from pypads.base import get_current_pads
            pads = get_current_pads()
            pads.cache.run_delete(run_id)
            debug("Cleared run cache after run " + run_id)

        pads.api.register_post_fn("cache_cleanup", cleanup_cache)


class PypadsCache(Cache):

    def __init__(self):
        super().__init__()
        self._run_caches = {}

    def run_cache(self, run_id=None):
        run = self.run_init(run_id)
        return self._run_caches.get(run)

    def _get_run(self, run_id=None):
        if run_id is None:
            run = mlflow.active_run()
        else:
            run = mlflow.get_run(run_id)
        return run

    def run_init(self, run_id=None):
        run = self._get_run(run_id)
        if not run:
            raise ValueError("No run is active. Couldn't init run cache.")
        if run not in self._run_caches:
            run_cache = PypadsRunCache(run)
            self._run_caches[run] = run_cache
            run_cache.register_cleanup_fn()
        return run

    def run_add(self, key, value, run_id=None):
        run = self.run_init(run_id)
        self._run_caches[run].add(key, value)

    def run_pop(self, key, run_id=None, default=None):
        run = self.run_init(run_id)
        return self._run_caches[run].pop(key, default=default)

    def run_remove(self, key, run_id=None):
        run = self.run_init(run_id)
        del self._run_caches[run][key]

    def run_get(self, key, run_id=None):
        run = self.run_init(run_id)
        return self._run_caches[run].get(key)

    def run_exists(self, key, run_id=None):
        run = self.run_init(run_id)
        return self._run_caches[run].exists(key)

    def run_clear(self, run_id=None):
        run = self.run_init(run_id)
        self._run_caches[run].clear()

    def run_delete(self, run_id=None):
        run = self.run_init(run_id)
        del self._run_caches[run]
