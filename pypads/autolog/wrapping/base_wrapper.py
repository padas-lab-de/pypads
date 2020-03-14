import inspect
from _py_abc import ABCMeta
from abc import abstractmethod
from logging import debug, warning

DEFAULT_ORDER = 1


class Context:
    __metaclass__ = ABCMeta

    def __init__(self, context):
        if context is None:
            class DummyClass:
                pass

            context = DummyClass
        self._c = context

    def overwrite(self, key, obj):
        setattr(self._c, key, obj)

    def store_wrap_meta(self, mapping, ref):
        try:
            if not hasattr(self._c, "_pypads_mapping_" + ref.__name__):
                setattr(self._c, "_pypads_mapping_" + ref.__name__, [])
            getattr(self._c, "_pypads_mapping_" + ref.__name__).append(mapping)

            if not hasattr(self._c, "_pypads_wrapped" + ref.__name__):
                setattr(self._c, "_pypads_name_" + ref.__name__, ref)
        except TypeError as e:
            debug("Can't set attribute '" + ref.__name__ + "' on '" + str(self._c) + "'. Omit wrapping.")
            return self._c

    def has_wrap_meta(self):
        return hasattr(self._c, "_pypads_wrapped")

    def store_original(self, wrappee):
        setattr(self._c, self.original_name(wrappee.__name__), wrappee)

    def has_original(self, wrappee):
        return hasattr(self._c, self.original_name(wrappee.__name__))

    def original_name(self, wrappee_name):
        return "_pypads_original_" + str(id(self._c)) + "_" + wrappee_name

    def original(self, wrappee_name):
        try:
            return getattr(self._c, self.original_name(wrappee_name))
        except AttributeError:
            for attr in dir(self._c):
                if attr.endswith("_" + wrappee_name) and attr.startswith("_pypads_original_"):
                    return getattr(self._c, attr)

    def is_class(self):
        return inspect.isclass(self._c)

    def is_module(self):
        return inspect.ismodule(self._c)

    def real_context(self, fn):
        """
        Find where the function was defined
        :return:
        """

        # If the context is not an class it has to define the function itself
        if not self.is_class():
            if hasattr(self._c, fn.__name__):
                return self
            else:
                warning("Context " + str(self._c) + " of type " + type(
                    self._c) + " doesn't define " + fn.__name__)
                return None

        # Find defining class by looking at the __dict__ and mro
        defining_class = None
        try:
            mro = self._c.mro()
            for clazz in mro[0:]:
                defining_class = self._c
                if hasattr(clazz, "__dict__") and fn.__name__ in defining_class.__dict__ and callable(
                        defining_class.__dict__[fn.__name__]):
                    break
        except Exception as e:
            warning("Couldn't get defining class of context '" + str(
                self._c) + ". " + str(e))
            return None

        if defining_class:
            return Context(defining_class)

    @property
    def container(self):
        return self._c

    def get_dict(self):
        return self._c.__dict__

    def __getattr__(self, item):
        return getattr(self._c, item)

    def __str__(self):
        return str(self._c)


class BaseWrapper:
    __metaclass__ = ABCMeta

    @classmethod
    @abstractmethod
    def wrap(cls, wrappee, ctx, mapping):
        raise NotImplementedError()

    @classmethod
    def _get_hooked_fns(cls, fn, mapping):
        """
        For a given fn find the hook functions defined in a mapping and configured in a configuration.
        :param fn:
        :param mapping:
        :return:
        """
        if not mapping.hooks:
            mapping.hooks = mapping.in_collection.get_default_fn_hooks()

        library = None
        version = None
        if mapping.in_collection is not None:
            library = mapping.in_collection.lib
            version = mapping.in_collection.lib_version
        hook_events_of_mapping = [hook.event for hook in mapping.hooks if hook.is_applicable(mapping=mapping, fn=fn)]
        output = []
        config = cls._get_current_config()
        for log_event, event_config in config["events"].items():
            configured_hook_events = event_config["on"]

            # Add by config defined parameters
            if "with" in event_config:
                hook_params = event_config["with"]
            else:
                hook_params = {}

            # Add an order
            if "order" in event_config:
                order = event_config["order"]
            else:
                order = DEFAULT_ORDER

            # If one configured_hook_events is in this config.
            if configured_hook_events == "always" or set(configured_hook_events) & set(hook_events_of_mapping):
                from pypads.base import get_current_pads
                pads = get_current_pads()
                fns = pads.function_registry.find_functions(log_event, lib=library, version=version)
                if fns:
                    for fn in fns:
                        output.append((fn, hook_params, order))
        output.sort(key=lambda t: t[2])
        return output

    @classmethod
    def _get_current_config(cls):
        from pypads.base import get_current_config
        return get_current_config(default={"events": {}, "recursive": True})
