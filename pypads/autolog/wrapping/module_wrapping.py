import inspect

from pypads import logger
from pypads.autolog.wrapping.base_wrapper import BaseWrapper


class ModuleWrapper(BaseWrapper):

    def __init__(self, pypads):
        super().__init__(pypads)
        self._punched_module_names = set()

    @property
    def punched_module_names(self):
        return self._punched_module_names

    def wrap(self, module, context, mapping_hit):
        """
        Function to wrap modules with pypads functionality
        :param module:
        :param mapping_hit:
        :return:
        """
        if module.__name__ not in self.punched_module_names or not context.has_wrap_meta(mapping_hit, module):
            self._pypads.wrap_manager.module_wrapper.punched_module_names.add(module.__name__)
            context.store_wrap_meta(mapping_hit, module)

            if not context.has_original(module):
                context.store_original(module)

            # Try to wrap every attr of the module
            # Only get entries defined directly in this module
            # https://stackoverflow.com/questions/22578509/python-get-only-classes-defined-in-imported-module-with-dir
            for name in list(filter(mapping_hit.applicable_filter(context),
                                    [m[0] for m in inspect.getmembers(module) if
                                     hasattr(m[1], "__module__") and m[1].__module__ == module.__name__])):
                attr = getattr(module, name)

                # Don't track imported modules
                if not inspect.ismodule(attr):
                    self._pypads.wrap_manager.wrap(attr, module, mapping_hit)
        else:
            logger.debug("Module " + str(module) + " already duck-punched.")
        return module
