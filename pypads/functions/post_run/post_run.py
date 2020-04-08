from abc import ABCMeta, abstractmethod

from pypads.functions.loggers.mixins import DependencyMixin, OrderMixin, TimedCallableMixin, IntermediateCallableMixin, \
    ConfigurableCallableMixin


class PostRunFunction(IntermediateCallableMixin, TimedCallableMixin, DependencyMixin, OrderMixin,
                      ConfigurableCallableMixin):
    __metaclass__ = ABCMeta
    """
    This class should be used to define new post run functions
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractmethod
    def _call(self, pads, *args, **kwargs):
        pass
