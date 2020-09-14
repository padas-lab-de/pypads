from pypads.app.call import Call
from pypads.utils.util import dict_merge


class LoggerEnv:

    def __init__(self, parameter, experiment_id, run_id, data=None):
        """
        :param parameter: Parameters given to the triggered logging env. Ex. defined on hooks.
        :param experiment_id: The id of the experiment.
        :param run_id: The id of the run.
        :param data: Additional data for the logger env.
        """
        self._data = data or {}
        self._parameter = parameter
        self._experiment_id = experiment_id
        self._run_id = run_id
        from pypads.app.pypads import get_current_pads
        self._pypads = get_current_pads()

    @property
    def data(self):
        return self._data

    @property
    def experiment_id(self):
        return self._experiment_id

    @property
    def run_id(self):
        return self._run_id

    @property
    def parameter(self):
        return self._parameter

    @property
    def pypads(self):
        return self._pypads


class InjectionLoggerEnv(LoggerEnv):

    def __init__(self, mappings, hook, callback, call: Call, parameter, experiment_id, run_id):
        super().__init__(parameter, experiment_id, run_id, data=dict_merge(*[m.mapping.values for m in mappings]))
        self._call = call
        self._callback = callback
        self._hook = hook
        self._mappings = mappings

    @property
    def call(self):
        return self._call

    @property
    def callback(self):
        return self._callback

    @property
    def hook(self):
        return self._hook

    @property
    def mappings(self):
        return self._mappings
