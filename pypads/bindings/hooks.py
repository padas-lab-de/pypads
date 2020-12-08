from typing import Iterable, Set

from pypads.app.misc.mixins import OrderMixin, DEFAULT_ORDER
from pypads.utils.logging_util import FileFormats

# Maps hooks to events

DEFAULT_HOOK_MAPPING = {
    "init": {"on": ["pypads_init"]},
    "parameters": {"on": ["pypads_fit"]},
    "hardware": {"on": ["pypads_fit"]},
    "output": {"on": ["pypads_fit", "pypads_predict"]},
    "input": {"on": ["pypads_fit"], "with": {"_pypads_write_format": FileFormats.text}},
    "metric": {"on": ["pypads_metric"]},
    "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metric"]},
    "log": {"on": ["pypads_log"]},
    "autolog": {"on": ["pypads_import"]}
}

class Hook:
    """
    Pypads hooks. Hooks are defined on function executions and trigger events to call logger functions.
    """

    def __init__(self, anchor, mapping):  # type: (Anchor, Mapping) -> Hook
        """
        Constructor for an hook.
        :param anchor: Anchor of the hook.
        :param mapping: Mapping creating the hook call.
        """
        self._anchor = anchor
        self._source = mapping

    @property
    def anchor(self):
        return self._anchor

    @property
    def source(self):  # type: () -> Mapping
        return self._source

    @property
    def library(self):  # type: () -> LibSelector
        return self._source.library

    def __eq__(self, other):
        return self.anchor == other.anchor

    def __hash__(self):
        return hash(self.anchor)

    def __str__(self):
        return "Hook[anchor=" + str(self.anchor) + ", lib=" + str(self.library) + "]"


class HookEventConfig(OrderMixin):
    def __init__(self, hook, event_name, parameters=None, *args, **kwargs):
        self._hook = hook
        self._event_name = event_name
        self._parameters = parameters
        super().__init__(*args, **kwargs)

    @property
    def anchor(self):
        return self._hook

    @property
    def event_name(self):
        return self._event_name

    @property
    def parameters(self):
        return self._parameters


class HookRegistry:
    """
    Class mapping hooks to events.
    """

    def __init__(self, pypads):
        self._pypads = pypads
        self._hook_event_mapping = {}

    def add_reference(self, event_name: str, *hook_names: str, order=DEFAULT_ORDER, parameters=None):
        for hook_name in hook_names:
            if hook_name not in self._hook_event_mapping:
                self._hook_event_mapping[hook_name] = set()
            self._hook_event_mapping[hook_name].add(HookEventConfig(hook_name, event_name, parameters, order=order))

    def get_configs_for_hook(self, hook: Hook) -> Set[HookEventConfig]:
        if hook.anchor.name not in self._hook_event_mapping:
            return set()
        else:
            return self._hook_event_mapping[hook.anchor.name]

    def get_logging_functions(self, *hooks: Hook):
        configs = []
        for hook in hooks:
            configs = configs + [(hook, c) for c in list(self.get_configs_for_hook(hook))]

        fns = []
        for hook, c in configs:
            found_fns = [(f, c) for f in
                         self._pypads.function_registry.get_functions(c.event_name, hook.library)]
            fns = fns + found_fns
        return fns

    @staticmethod
    def from_dict(pypads, hook_mapping):
        """
        Build a hook registry from given dict mapping.
        :param pypads: Owning PyPads instance
        :param hook_mapping: A dict containing the mapping information.
        :return:
        """
        registry = HookRegistry(pypads)

        if hook_mapping is None:
            hook_mapping = DEFAULT_HOOK_MAPPING

        for key, value in hook_mapping.items():
            parameters = value["with"] if "with" in value else {}
            hook_names = value["on"]
            order = value["order"] if "order" in value else DEFAULT_ORDER
            if isinstance(hook_names, Iterable):
                registry.add_reference(key, *hook_names, order=order, parameters=parameters)
            else:
                registry.add_reference(key, hook_names, order=order, parameters=parameters)
        return registry
