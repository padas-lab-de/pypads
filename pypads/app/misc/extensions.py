from pypads.app.misc.mixins import OrderMixin


class Plugin(OrderMixin):
    """
    A plugin holding instances of a given type of extension elements.
    """

    def __init__(self, type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = type

    @property
    def type(self):
        return self._type

    @property
    def _get_meta(self):
        """
        Todo return meta (for example where plugin was defined)
        :return:
        """
        return self.__module__

    def __hash__(self):
        return hash(self.__class__)

    def __eq__(self, other):
        """
        Plugins are to be considered equal if they are of the same class. TODO Singleton?
        :param other:
        :return:
        """
        return self.__class__ == other.__class__


class ExtendableMixin:
    """
    Abstract class for plugin managers.
    """

    def __init__(self, plugin_list=None, *args, **kwargs):
        """
        Abstract class for plugin managers.
        :param instances: Initial plugins which should be added.
        """
        # if instances is not None:
        #     if not isinstance(instances, Iterable):
        #         instances = [instances]
        #     self._instances = instances
        # else:
        super().__init__(*args, **kwargs)
        self._instances = plugin_list

    def __getattr__(self, item):
        """ Try to find a fitting variable / function. Older definitions overwrite newer. """
        if item is "__get_instance":
            return self.__get_instance

        instances = list(self._instances)
        instances.sort(key=lambda instance: instance.order)
        for i in instances:
            if hasattr(i, item):
                return getattr(i, item)

    def __get_instance(self, index):
        return self._instances[index]
