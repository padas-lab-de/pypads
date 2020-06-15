from pypads import logger

from pypads.autolog.wrapping.base_wrapper import BaseWrapper, Context


class ClassWrapper(BaseWrapper):

    def __init__(self, pypads):
        super().__init__(pypads)
        self._punched_class_names = set()

    @property
    def punched_class_names(self):
        return self._punched_class_names

    def wrap(self, clazz, context, matched_mapping):
        """
            Wrap a class in given ctx with pypads functionality
            :param clazz:
            :param context:
            :param matched_mapping:
            :return:
            """
        if clazz.__name__ not in self.punched_class_names or not context.has_wrap_meta(matched_mapping.mapping, clazz):
            try:
                context.store_wrap_meta(matched_mapping, clazz)
            except Exception:
                return clazz
            self.punched_class_names.add(clazz.__name__)

            if not context.has_original(clazz):
                context.store_original(clazz)

            # Module was changed and should be added to the list of modules which have been changed
            if hasattr(clazz, "__module__"):
                self._pypads.wrap_manager.module_wrapper.add_punched_module_name(clazz.__module__)

            # Try to wrap every attr of the class
            for name in list(filter(
                    matched_mapping.mapping.applicable_filter(
                        Context(clazz, ".".join([context.reference, clazz.__name__]))),
                    dir(clazz))):
                self._pypads.wrap_manager.wrap(getattr(clazz, name), clazz, matched_mapping)

            # Override class on module
            context.overwrite(clazz.__name__, clazz)
        else:
            logger.debug("Class " + str(clazz) + "already duck-puched.")
        return clazz
