from _py_abc import ABCMeta
from abc import abstractmethod

from pypads.functions.analysis.time_keeper import timed
from pypads.util import is_package_available


class NoCallAllowedError(Exception):
    """
    Exception to denote that a callable couldn't be called, but isn't essential.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MissingDependencyError(NoCallAllowedError):
    """
    Exception to be thrown if a dependency is missing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SuperStop:
    """
    This class resolves the issue TypeError: object.__init__() takes exactly one argument by being the last class
    in a mro and ommitting all arguments. This should be always last in the mro()!
    """

    def __init__(self, *args, **kwargs):
        mro = self.__class__.mro()
        if SuperStop in mro:
            if len(mro) - 2 != mro.index(SuperStop):
                raise ValueError("SuperStop ommitting arguments in " + str(self.__class__)
                                 + " super() callstack: " + str(mro))
        super().__init__()


class OrderMixin(SuperStop):
    """
    Object defining an order attribute to denote its priority.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, order=0, **kwargs):
        self._order = order
        super().__init__(*args, **kwargs)

    def order(self):
        return self._order


class CallableMixin(SuperStop):
    """
    Object defining a _call method which can be overwritten.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.__real_call__(*args, **kwargs)

    @abstractmethod
    def __real_call__(self, *args, **kwargs):
        pass


class DependencyMixin(CallableMixin):
    """
    Callable being able to be disabled / enabled depending on package availability.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    @abstractmethod
    def _needed_packages():
        """
        Overwrite this to provide your package names.
        :return: List of needed packages by the logger.
        """
        return []

    def _check_dependencies(self):
        """
        Raise error if dependencies are missing.

        """
        missing = []
        for package in self._needed_packages():
            if not is_package_available(package):
                missing.append(package)
        if len(missing) > 0:
            raise MissingDependencyError("Can't log " + str(self) + ". Missing dependencies: " + ", ".join(missing))

    def __call__(self, *args, **kwargs):
        self._check_dependencies()
        return super().__call__(*args, **kwargs)


class IntermediateCallableMixin(CallableMixin):
    """
    Callable being able to be disable / enabled on nested / intermediate runs.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, nested=True, intermediate=True, **kwargs):
        self._intermediate = intermediate
        self._nested = nested
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        from pypads.pypads import is_nested_run
        if self._nested or not is_nested_run():
            from pypads.pypads import is_intermediate_run
            if self._intermediate or not is_intermediate_run():
                return super().__call__(*args, **kwargs)
        raise NoCallAllowedError("Call wasn't allowed by intermediate / nested settings of the current run.")

    @property
    def nested(self):
        return self._nested

    @property
    def intermediate(self):
        return self._intermediate


class TimedCallableMixin(CallableMixin):
    __metaclass__ = ABCMeta
    """
    Callable tracking its own execution time.
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        c = super().__call__
        _return, time = timed(lambda: c(*args, **kwargs))
        return _return, time


class DefensiveCallableMixin(CallableMixin):
    __metaclass__ = ABCMeta
    """
    Callable handling errors produced by itself.
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, ctx, *args, _pypads_env=None, **kwargs):
        try:
            return super().__call__(ctx, *args, _pypads_env=_pypads_env, **kwargs)
        except KeyboardInterrupt:
            return self._handle_error(*args, ctx=ctx, _pypads_env=_pypads_env, error=Exception("KeyboardInterrupt"),
                                      **kwargs)
        except Exception as e:
            return self._handle_error(*args, ctx=ctx, _pypads_env=_pypads_env, error=e, **kwargs)

    @abstractmethod
    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        raise NotImplementedError()


class ConfigurableCallableMixin(CallableMixin):
    __metaclass__ = ABCMeta
    """
    Callable storing additional creation args as fields to be accessible later on.
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        self._kwargs = kwargs
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        super().__call__(*args, **{**self._kwargs, **kwargs})
