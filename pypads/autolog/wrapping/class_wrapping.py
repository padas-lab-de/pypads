from pypads import logger

from pypads.autolog.wrapping.base_wrapper import BaseWrapper


class ClassWrapper(BaseWrapper):

    def __init__(self, pypads):
        super().__init__(pypads)
        self._punched_class_names = set()

    @property
    def punched_class_names(self):
        return self._punched_class_names

    def wrap(self, clazz, context, mapping_hit):
        """
            Wrap a class in given ctx with pypads functionality
            :param clazz:
            :param context:
            :param mapping_hit:
            :return:
            """
        if clazz.__name__ not in self.punched_class_names or not context.has_wrap_meta(mapping_hit.mapping, clazz):
            try:
                context.store_wrap_meta(mapping_hit, clazz)
            except Exception:
                return clazz
            self.punched_class_names.add(clazz.__name__)

            if not context.has_original(clazz):
                context.store_original(clazz)

            # Module was changed and should be added to the list of modules which have been changed
            if hasattr(clazz, "__module__"):
                self._pypads.wrap_manager.module_wrapper.punched_module_names.add(clazz.__name__)

            # Try to wrap every attr of the class
            for name in list(filter(mapping_hit.mapping.applicable_filter(context), dir(clazz))):
                self._pypads.wrap_manager.wrap(getattr(clazz, name), clazz, mapping_hit)

            # Override class on module
            context.overwrite(clazz.__name__, clazz)
        else:
            logger.debug("Class " + str(clazz) + "already duck-puched.")
        return clazz
