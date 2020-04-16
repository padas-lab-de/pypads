import inspect

from pypads import logger
from pypads.autolog.hook import make_hook_applicable_filter
from pypads.autolog.wrapping.base_wrapper import BaseWrapper


class ModuleWrapper(BaseWrapper):

    def __init__(self, pypads):
        super().__init__(pypads)
        self._punched_module_names = set()

    @property
    def punched_module_names(self):
        return self._punched_module_names

    def wrap(self, module, context, mapping):
        """
        Function to wrap modules with pypads functionality
        :param module:
        :param mapping:
        :return:
        """
        if module.__name__ not in self.punched_module_names or not context.has_wrap_meta(mapping, module):
            self._pypads.wrap_manager.module_wrapper.punched_module_names.add(module.__name__)
            context.store_wrap_meta(mapping, module)

            if not context.has_original(module):
                context.store_original(module)

            # Get default hooks
            if not mapping.hooks:
                mapping.hooks = mapping.in_collection.get_default_module_hooks()

            # Try to wrap every attr of the module
            if mapping.hooks:
                for hook in mapping.hooks:
                    # Only get entries defined directly in this module
                    # https://stackoverflow.com/questions/22578509/python-get-only-classes-defined-in-imported-module-with-dir
                    for name in list(filter(make_hook_applicable_filter(hook, module, mapping),
                                            [m[0] for m in inspect.getmembers(module) if
                                             hasattr(m[1], "__module__") and m[1].__module__ == module.__name__])):
                        attr = getattr(module, name)

                        # Don't track imported modules
                        if not inspect.ismodule(attr):
                            self._pypads.wrap_manager.wrap(attr, module, mapping)

            # Add found classes to the tracking
            # for name in find_applicable_hooks(ctx, mapping):
            #     algorithm_mapping = AlgorithmMapping(mapping.reference + "." + name, mapping.library,
            #                                          mapping.algorithm,
            #                                          mapping.file, mapping.hooks)
            #     algorithm_mapping.in_collection = mapping.in_collection
            #     from pypads.autolog.wrapping.wrapping import _add_found_class
            #     _add_found_class(algorithm_mapping)
        else:
            logger.debug("Module " + str(module) + " already duck-punched.")
        return module
