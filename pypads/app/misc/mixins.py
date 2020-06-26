import uuid
from _py_abc import ABCMeta
from abc import abstractmethod
from typing import List

from pypads.utils.util import is_package_available, dict_merge

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
    def __init__(self, *args, order=DEFAULT_ORDER, **kwargs):
        self._order = order
        super().__init__(*args, **kwargs)

    def order(self):
        return self._order

    @staticmethod
    def sort(collection, reverse=False):  # type: (List[OrderMixin]) -> List[OrderMixin]
        copy = collection.copy()
        copy.sort(key=lambda e: e.order(), reverse=reverse)
        return copy

    @staticmethod
    def sort_mutable(collection, reverse=False):  # type: (List[OrderMixin]) -> None
        collection.sort(key=lambda e: e.order(), reverse=reverse)


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
        packages = self._needed_packages()
        if packages is not None:
            for package in packages:
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
        from pypads.app.pypads import is_nested_run
        if self._nested or not is_nested_run():
            from pypads.app.pypads import is_intermediate_run
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


class ValidateableMixin(SuperStop):
    __metaclass__ = ABCMeta
    """ This class implements basic logic for validating a validateble object"""

    # noinspection PyBroadException
    def __init__(self, *args, metadata, schema=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._schema = schema
        self.validate(metadata=metadata, **kwargs)

    @abstractmethod
    def validate(self, metadata, **kwargs):
        pass


class MetadataMixin(ValidateableMixin):
    """
    Base object for tracked objects that manage metadata. A MetadataEntity manages and id and a dict of metadata.
    The metadata should contain all necessary non-binary data to describe an entity.
    """
    # Metadata attributes
    METADATA = 'metadata'
    CREATED_AT = 'created_at'
    EXPERIMENT_ID = 'experiment_id'
    RUN_ID = 'run_id'

    @abstractmethod
    def __init__(self, *args, metadata: dict, pads=None, **kwargs):
        if pads is None:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
        self.pads = pads
        run = self.pads.api.active_run()
        import time
        self._metadata = {
            **{"id": uuid.uuid4().__str__(), self.CREATED_AT: time.time(), self.EXPERIMENT_ID: run.info.experiment_id,
               self.RUN_ID: run.info.run_id}, **metadata}

        super().__init__(*args, **{self.METADATA: metadata, **kwargs})

    @property
    def id(self):
        """
        returns the unique id of the data set. Data sets will be managed on the basis of this id
        :return: string
        """
        return self.metadata.get("id", None)

    @id.setter
    def id(self, _id):
        """
        used for updating the id after the undlerying generic has assigned one
        :param _id: id, ideally an url
        :return:
        """
        self.metadata["id"] = _id

    @property
    def name(self):
        """
        returns the name of this object, which is expected in field "name" of the metadata. If this field does not
        exist, the id is returned
        :return:
        """
        return self.metadata.get("name", None)

    @name.setter
    def name(self, name):
        self.metadata["name"] = name

    @property
    def created_at(self):
        return self.metadata.get(self.CREATED_AT, None)

    @property
    def run_id(self):
        return self.metadata.get(self.RUN_ID, None)

    @property
    def experiment_id(self):
        return self.metadata.get(self.EXPERIMENT_ID, None)

    @property
    def metadata(self):
        return self._metadata

    def merge_metadata(self, metadata: dict):
        self._metadata = dict_merge(self.metadata, metadata)
