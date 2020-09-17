import traceback
from abc import abstractmethod, ABCMeta
from typing import List, Union, Tuple, Set

from pypads import logger
from pypads.app.misc.inheritance import SuperStop
from pypads.importext.versioning import LibSelector, VersionNotFoundException
from pypads.model.domain import LibraryModel
from pypads.model.metadata import ModelObject

DEFAULT_ORDER = 1


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


class OrderMixin(SuperStop):
    """
    Object defining an order attribute to denote its priority. Smallest to largest!
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, order=DEFAULT_ORDER, **kwargs):
        self._order = order
        super().__init__(*args, **kwargs)

    @property
    def order(self):
        return self._order

    @staticmethod
    def sort(collection, reverse=False):  # type: (List[OrderMixin]) -> List[OrderMixin]
        copy = collection.copy()
        copy.sort(key=lambda e: e.order, reverse=reverse)
        return copy

    @staticmethod
    def sort_mutable(collection, reverse=False):  # type: (List[OrderMixin]) -> None
        collection.sort(key=lambda e: e.order, reverse=reverse)


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

    """
    Overwrite this to provide your package names.
    :return: List of needed packages by the logger.
    """
    _dependencies: Set[Union[LibSelector, str, Tuple[str, str]]] = set()

    @property
    def dependencies(self):
        return self._to_lib_selectors(self._dependencies)

    @staticmethod
    def _to_lib_selectors(dependencies: Set[Union[LibSelector, str, Tuple[str, str]]]) -> Set[LibSelector]:
        selectors = set()
        for d in dependencies:
            selectors.add(LibSelector(name=d[0], constraint=d[1]) if isinstance(d, tuple) else LibSelector(
                name=d) if not isinstance(d, LibSelector) else d)
        return selectors

    def _check_dependencies(self):
        """
        Raise error if dependencies are missing.
        """
        missing = []
        selectors = self.dependencies
        if selectors is not None:
            for selector in selectors:
                try:
                    if not selector.is_installed():
                        missing.append(selector)
                except VersionNotFoundException as e:
                    # TODO couldn't get version allow execution for now
                    pass
        if len(missing) > 0:
            raise MissingDependencyError(
                "Can't log " + str(self) + ". Missing dependencies: " + ", ".join([str(d) for d in missing]))

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
        from pypads.app.pypads import is_nested_run
        if self._nested or not is_nested_run():
            from pypads.app.pypads import is_intermediate_run
            if self._intermediate or not is_intermediate_run():
                return super().__call__(*args, **kwargs)
        raise NoCallAllowedError("Call wasn't allowed by intermediate / nested settings of the current run.")

    @property
    def allow_nested(self):
        return self._nested

    @property
    def allow_intermediate(self):
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
        from pypads.injections.analysis.time_keeper import timed
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
        except NoCallAllowedError:
            # Ignore for now
            pass
        except Exception as e:
            import traceback
            logger.debug(traceback.format_exc())
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

    @property
    def static_parameters(self):
        return self._kwargs


class LibrarySpecificMixin(SuperStop):
    """
    A class only being applicable for a certain library.
    """
    __metaclass__ = ABCMeta

    supported_libraries: Set[LibSelector] = set()

    def allows_any(self, lib_selector: LibSelector):
        libraries = self.supported_libraries
        return len(libraries) == 0 or any([s.allows_any(lib_selector) for s in libraries])

    def allows(self, version):
        libraries = self.supported_libraries
        return len(libraries) == 0 or any([s.allows(version) for s in libraries])

    def is_applicable(self, lib_selector: LibSelector, only_name=True):
        if self.allows_any(lib_selector):
            return True
        if only_name:
            for s in self.supported_libraries:
                if s.name == lib_selector.name:
                    return True
        return False


class FunctionHolderMixin(CallableMixin):
    """
    Holds the given function in a timed callable.
    """

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, **kwargs)
        self._fn = fn

    @property
    def fn(self):
        return self._fn

    def __real_call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    def __str__(self):
        return self._fn.__name__


class ProvenanceMixin(ModelObject, metaclass=ABCMeta):
    """
    Class extracting its library reference automatically if possible.
    """

    def __init__(self, *args, lib_model: LibraryModel = None, **kwargs):
        super().__init__(*args, **kwargs)
        if lib_model is None:
            setattr(self, "defined_in", self._get_library_descriptor())
        else:
            setattr(self, "defined_in", lib_model)

        if not hasattr(self, "uri") or getattr(self, "uri") is None and hasattr(self, "uid") and hasattr(self, "is_a"):
            setattr(self, "uri", "{}#{}".format(getattr(self, "is_a"), self.uid))

    def _get_library_descriptor(self) -> LibraryModel:
        """
        Try to extract the defining package of this class.
        :return:
        """
        # TODO extract reference to self package
        try:
            name = self.__module__.split(".")[0]
            from pypads.utils.util import find_package_version
            version = find_package_version(name)
            return LibraryModel(name=name, version=version, extracted=True)
        except Exception:
            return LibraryModel(name="__unkown__", version="0.0", extracted=True)


class BaseDefensiveCallableMixin(DefensiveCallableMixin):
    """
    Defensive callable ignoring errors but printing a warning to console.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, error_message=None, **kwargs):
        self._message = error_message if error_message else "Couldn't execute {}, because of exception: {} \nTrace:\n{}"
        super().__init__(*args, **kwargs)

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        logger.warning(self._message.format("{}.{}".format(self.__class__.__name__, self.__name__), str(error),
                                            traceback.format_exc()))
