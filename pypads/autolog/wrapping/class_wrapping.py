from pypads import logger

from pypads.autolog.hook import find_applicable_hooks
from pypads.autolog.wrapping.base_wrapper import BaseWrapper


class ClassWrapper(BaseWrapper):

    def __init__(self, pypads):
        super().__init__(pypads)
        self._punched_class_names = set()

    @property
    def punched_class_names(self):
        return self._punched_class_names

    def wrap(self, clazz, context, mapping):
        """
            Wrap a class in given ctx with pypads functionality
            :param clazz:
            :param context:
            :param mapping:
            :return:
            """
        if clazz.__name__ not in self.punched_class_names or not context.has_wrap_meta(mapping, clazz):
            try:
                context.store_wrap_meta(mapping, clazz)
            except Exception:
                return clazz
            self.punched_class_names.add(clazz.__name__)

            if not context.has_original(clazz):
                context.store_original(clazz)

            # Module was changed and should be added to the list of modules which have been changed
            if hasattr(clazz, "__module__"):
                self._pypads.wrap_manager.module_wrapper.punched_module_names.add(clazz.__name__)

            # Get default hooks
            if not mapping.hooks:
                mapping.hooks = mapping.in_collection.get_default_class_hooks()

            # Try to wrap every attr of the class
            for name, c, mapping in find_applicable_hooks(clazz, mapping):
                self._pypads.wrap_manager.wrap(getattr(clazz, name), c, mapping)

            # Override class on module
            reference_name = mapping.reference.rsplit('.', 1)[-1]
            context.overwrite(reference_name, clazz)
        else:
            logger.debug("Class " + str(clazz) + "already duck-puched.")
        return clazz
