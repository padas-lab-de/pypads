import inspect
from typing import Set

from pypads import logger
from pypads.importext.mappings import MatchedMapping
from pypads.importext.wrapping.base_wrapper import BaseWrapper, Context


class ModuleWrapper(BaseWrapper):

    def __init__(self, pypads):
        super().__init__(pypads)
        self._punched_module_names = set()

    @property
    def punched_module_names(self):
        return self._punched_module_names

    def add_punched_module_name(self, name):
        self._punched_module_names.add(name)

    def wrap(self, module, context, matched_mappings: Set[MatchedMapping]):
        """
        Function to wrap modules with pypads functionality
        :param module:
        :param context:
        :param matched_mappings:
        :return:
        """
        if module.__name__ not in self.punched_module_names:
            self._pypads.wrap_manager.module_wrapper.add_punched_module_name(module.__name__)
            for matched_mapping in matched_mappings:
                context.store_wrap_meta(matched_mapping, module)

            if not context.has_original(module):
                context.store_original(module)

            # Try to wrap every attr of the module
            # Only get entries defined directly in this module
            # https://stackoverflow.com/questions/22578509/python-get-only-classes-defined-in-imported-module-with-dir
            attrs = {}
            for matched_mapping in matched_mappings:
                for name in list(filter(matched_mapping.mapping.applicable_filter(
                        Context(module, ".".join([context.reference, module.__name__]))),
                        [m for m, _ in inspect.getmembers(module, lambda x: hasattr(x,
                                                                                    "__module__") and x.__module__ == module.__name__)])):
                    attr = getattr(module, name)
                    if attr not in attrs:
                        attrs[attr] = set()
                    else:
                        attrs[attr].add(matched_mapping)

            for attr, mm in attrs.items():
                # Don't track imported modules
                if not inspect.ismodule(attr):
                    self._pypads.wrap_manager.wrap(attr, module, mm)
        else:
            logger.debug("Module " + str(module) + " already duck-punched.")
        return module
