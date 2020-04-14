import inspect
from _py_abc import ABCMeta
from abc import abstractmethod
from copy import copy

from loguru import logger

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

    def has_wrap_meta(self, mapping, wrappee):
        if not inspect.isfunction(wrappee):
            holder = wrappee
        else:
            holder = self._c
        # for k in holder.__dict__:
        #     if k.startswith("_pypads_mapping_"):
        #         if mapping in getattr(holder, k):
        #             return True
        if hasattr(holder, "_pypads_mapping_" + wrappee.__name__):
            if mapping in getattr(holder, "_pypads_mapping_" + wrappee.__name__):
                return True
        return False

    def store_wrap_meta(self, mapping, wrappee):
        try:
            if not inspect.isfunction(wrappee):
                holder = wrappee
            else:
                holder = self._c
            # Set self reference
            if not hasattr(holder, "_pypads_mapping_" + wrappee.__name__):
                setattr(holder, "_pypads_mapping_" + wrappee.__name__, [])
            getattr(holder, "_pypads_mapping_" + wrappee.__name__).append(mapping)
        except TypeError as e:
            logger.debug("Can't set attribute '" + wrappee.__name__ + "' on '" + str(self._c) + "'.")
            return self._c

    def store_original(self, wrappee):
        try:
            if not inspect.isfunction(wrappee):
                holder = wrappee
            else:
                holder = self._c
            setattr(holder, self.original_name(wrappee), copy(wrappee))
        except TypeError as e:
            logger.debug("Can't set attribute '" + wrappee.__name__ + "' on '" + str(self._c) + "'.")
            return self._c

    def has_original(self, wrappee):
        return hasattr(self._c, self.original_name(wrappee)) or hasattr(wrappee,
                                                                        self.original_name(wrappee))

    def defined_stored_original(self, wrappee):
        if not inspect.isfunction(wrappee):
            return self.original_name(wrappee) in wrappee.__dict__
        else:
            return self.original_name(wrappee) in self._c.__dict__

    def original_name(self, wrappee):
        return "_pypads_original_" + str(wrappee.__name__)

    def original(self, wrappee):
        if not inspect.isfunction(wrappee) and not inspect.ismethod(wrappee):
            try:
                return getattr(wrappee, self.original_name(wrappee))
            except AttributeError:
                for attr in dir(wrappee):
                    if attr.endswith("_" + wrappee.__name__) and attr.startswith("_pypads_original_"):
                        return getattr(wrappee, attr)
        else:
            try:
                return getattr(self._c, self.original_name(wrappee))
            except AttributeError:
                for attr in dir(self._c):
                    if attr.endswith("_" + wrappee.__name__) and attr.startswith("_pypads_original_"):
                        return getattr(self._c, attr)

    def is_class(self):
        return inspect.isclass(self._c)

    def is_module(self):
        return inspect.ismodule(self._c)

    def real_context(self, fn_name):
        """
        Find where the function was defined
        :return:
        """

        # If the context is not an class it has to define the function itself
        if not self.is_class():
            if hasattr(self._c, fn_name):
                return self
            else:
                logger.warning("Context " + str(self._c) + " of type " + type(
                    self._c) + " doesn't define " + fn_name)
                return None

        # Find defining class by looking at the __dict__ and mro
        defining_class = None
        try:
            mro = self._c.mro()
            for clazz in mro[0:]:
                defining_class = clazz
                if hasattr(clazz, "__dict__") and fn_name in defining_class.__dict__:
                    if callable(defining_class.__dict__[fn_name]):
                        break
                    else:
                        # TODO workaround for <sklearn.utils.metaestimators._IffHasAttrDescriptor object at 0x121e56810> again
                        break
        except Exception as e:
            logger.warning("Couldn't get defining class of context '" + str(
                self._c) + ".")
            return self._c

        if defining_class and defining_class is not object:
            return Context(defining_class)
        return self._c

    @property
    def container(self):
        return self._c

    def get_dict(self):
        return self._c.__dict__

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
                from pypads.pypads import get_current_pads
                pads = get_current_pads()
                fns = pads.function_registry.find_functions(log_event, lib=library, version=version)
                if fns:
                    for fn in fns:
                        output.append((fn, hook_params, order))
        output.sort(key=lambda t: t[2])
        return output

    @classmethod
    def _get_current_config(cls):
        from pypads.pypads import get_current_config
        return get_current_config(default={"events": {}, "recursive": True})
