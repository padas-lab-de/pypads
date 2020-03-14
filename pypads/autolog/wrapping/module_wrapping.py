import inspect
from logging import debug

from pypads.autolog.hook import find_applicable_hooks
from pypads.autolog.wrapping.base_wrapper import BaseWrapper

punched_module_names = set()


class ModuleWrapper(BaseWrapper):

    @classmethod
    def wrap(cls, module, ctx, mapping):
        """
        Function to wrap modules with pypads functionality
        :param module:
        :param mapping:
        :return:
        """
        if module.__name__ not in punched_module_names:
            punched_module_names.add(module.__name__)
            ctx.store_wrap_meta(mapping, module)
            ctx.store_original(module)

            # Get default hooks
            if not mapping.hooks:
                mapping.hooks = mapping.in_collection.get_default_module_hooks()

            # Try to wrap every attr of the module
            from pypads.autolog.wrapping.wrapping import wrap

            for name, m, mapping in find_applicable_hooks(module, mapping):
                attr = getattr(module, name)

                # Don't track imported modules
                if not inspect.ismodule(attr):
                    wrap(attr, m, mapping)

            # Add found classes to the tracking
            # for name in find_applicable_hooks(ctx, mapping):
            #     algorithm_mapping = AlgorithmMapping(mapping.reference + "." + name, mapping.library,
            #                                          mapping.algorithm,
            #                                          mapping.file, mapping.hooks)
            #     algorithm_mapping.in_collection = mapping.in_collection
            #     from pypads.autolog.wrapping.wrapping import _add_found_class
            #     _add_found_class(algorithm_mapping)
        else:
            debug("Module " + str(module) + " already duck-punched.")
        return module
