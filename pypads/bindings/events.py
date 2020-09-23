from typing import Iterable, Union

from pypads.bindings.event_types import EventType
from pypads.bindings.hooks import Hook
from pypads.importext.versioning import LibSelector
from pypads.injections.analysis.parameters import ParametersILF
from pypads.injections.loggers.data_flow import OutputILF, InputILF
from pypads.injections.loggers.debug import Log, LogInit
from pypads.injections.loggers.hardware import CpuILF, RamILF, DiskILF
from pypads.injections.loggers.metric import MetricILF
from pypads.injections.loggers.mlflow.mlflow_autolog import MlflowAutologger
from pypads.utils.logging_util import FileFormats

# maps events to loggers
# Default event mappings. We allow to log parameters, output defor input
DEFAULT_LOGGING_FNS = {
    "parameters": ParametersILF(),
    "output": OutputILF(_pypads_write_format=FileFormats.text),
    "input": InputILF(_pypads_write_format=FileFormats.text),
    "hardware": [CpuILF(_pypads_write_format=FileFormats.text), RamILF(_pypads_write_format=FileFormats.text),
                 DiskILF(_pypads_write_format=FileFormats.text)],
    "metric": MetricILF(),
    "autolog": MlflowAutologger(),
    # "pipeline": PipelineTrackerILF(_pypads_pipeline_type="normal", _pypads_pipeline_args=False),
    "log": Log(),
    "init": LogInit()
}


class Event:
    """
    Pypads event. Every event triggers multiple logging functions to be executed. Events are triggered by hooks.
    """

    def __init__(self, event_type: EventType, triggered_by: Hook):
        """
        Constructor for an event.
        :param event_type: Type of the event.
        :param triggered_by: Source which triggered the event.
        """
        self._event_type = event_type
        self._source = triggered_by

    @property
    def name(self):
        return self._event_type.name

    @property
    def description(self):
        return self._event_type.description

    @property
    def source(self):
        return self._source


class FunctionRegistry:

    def __init__(self, pypads):
        self._pypads = pypads
        self._fns = {}

    @staticmethod
    def from_dict(pypads, mapping):
        """
        Build a function registry from given dict mapping.
        :param mapping: A dict containing the mapping information.
        :return:
        """
        registry = FunctionRegistry(pypads)

        if mapping is None:
            mapping = DEFAULT_LOGGING_FNS

        for key, value in mapping.items():
            if isinstance(value, Iterable):
                registry.add_function(key, *value)
            elif callable(value):
                registry.add_function(key, value)
        return registry

    def add_function(self, event_name: str, *fns):
        """
        Add all given functions behind a key
        :param event_name: Event key for the functions
        :param fns: Functions to add
        :return:
        """
        if event_name not in self._fns:
            self._fns[event_name] = set()
        for fn in fns:
            self._fns[event_name].add(fn)

    def has(self, event_name: Union[str,tuple]):
        """
        Check if at least one function with event key is in map.
        :param event_name: Key of the function
        :return: true if has function
        """
        return event_name in self._fns

    def get_functions(self, event_name, lib_selector: LibSelector):
        if not self.has(event_name):
            return set()
        fns = self._fns[event_name] if isinstance(self._fns[event_name], Iterable) else [self._fns[event_name]]

        fitting_fns = []
        for fn in fns:
            fitting_fns = fitting_fns + [(lib.specificity, fn) for lib in fn.supported_libraries if
                                         lib.allows_any(lib_selector)]

        # Filter for specificity and identity
        identities = {}
        filtered_fns = set()
        for spec, fn in fitting_fns:
            if not hasattr(fn, "identity") or fn.identity is None:
                filtered_fns.add(fn)
            elif fn.identity in identities:
                # If we are more specific and have the same identity remove old fn
                if identities[fn.identity][0] <= spec:
                    if identities[fn.identity][0] < spec:
                        if fn.identity in identities:
                            filtered_fns.remove(identities[fn.identity][1])
                    filtered_fns.add(fn)
                    identities[fn.identity] = (spec, fn)
            else:
                # If not seen add it
                filtered_fns.add(fn)
                identities[fn.identity] = (spec, fn)
        return filtered_fns
