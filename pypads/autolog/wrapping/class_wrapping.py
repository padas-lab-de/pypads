from logging import debug

from pypads.autolog.hook import find_applicable_hooks
from pypads.autolog.wrapping.base_wrapper import BaseWrapper

punched_classes = set()


class ClassWrapper(BaseWrapper):

    @classmethod
    def wrap(cls, clazz, ctx, mapping):
        """
            Wrap a class in given ctx with pypads functionality
            :param clazz:
            :param ctx:
            :param mapping:
            :return:
            """
        global punched_classes
        if clazz not in punched_classes:
            punched_classes.add(clazz)
            ctx.store_wrap_meta(mapping, clazz)
            ctx.store_original(clazz)

            # Module was changed and should be added to the list of modules which have been changed
            if hasattr(clazz, "__module__"):
                from pypads.autolog.wrapping.module_wrapping import punched_module_names
                punched_module_names.add(clazz.__module__)

            # Get default hooks
            if not mapping.hooks:
                mapping.hooks = mapping.in_collection.get_default_class_hooks()

            # Try to wrap every attr of the class
            from pypads.autolog.wrapping.wrapping import wrap

            for name, c, mapping in find_applicable_hooks(clazz, mapping):
                wrap(getattr(clazz, name), c, mapping)

            # Override class on module
            reference_name = mapping.reference.rsplit('.', 1)[-1]
            if ctx is not None:
                setattr(ctx, reference_name, clazz)
        else:
            debug("Class " + str(clazz) + "already duck-puched.")
        return clazz
