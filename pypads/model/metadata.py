from abc import abstractmethod, ABCMeta
from collections import deque
from copy import deepcopy
from typing import Type, List

from pydantic import validate_model, BaseModel, ValidationError, ConfigError
from pydantic.version import VERSION

from pypads.app.misc.inheritance import SuperStop
from pypads.model.models import BaseStorageModel, get_reference
from pypads.utils.logging_util import jsonable_encoder
from pypads.utils.util import has_direct_attr, persistent_hash


class ModelInterface(SuperStop):

    @classmethod
    @abstractmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        raise NotImplementedError("A model cls has to be defined for a class linked to a model.")

    @abstractmethod
    def model(self) -> Type[BaseModel]:
        raise NotImplementedError("A function how to access the model of the class has to be defined.")

    @abstractmethod
    def schema(self):
        raise NotImplementedError("A function how to access the schema of the class has to be defined.")

    @abstractmethod
    def json(self, *args, **kwargs):
        raise NotImplementedError("A function how to convert a class to its json representation has to be defined.")

    @abstractmethod
    def validate(self):
        raise NotImplementedError("A function how to validate the schema for the class has to be defined.")

    def get_model_fields(self):
        """
        Return the field names of a model.
        :return:
        """
        return self.get_model_cls().__fields__


class ModelObject(ModelInterface, metaclass=ABCMeta):
    """
    An object building the model from itself on the fly.
    """
    _schema_reference = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        fields = set(self.get_model_fields().keys())

        # Add given fields to metadata object if not already existing
        for key, val in kwargs.items():
            if key in fields and not has_direct_attr(self, key):
                setattr(self, key, val)
                fields.remove(key)

        # Add defaults which are not given
        for key in fields:
            if not has_direct_attr(self, key) and self.get_model_fields() and (
                    not hasattr(self.__class__, key) or not isinstance(getattr(self.__class__, key), property)):
                setattr(self, key, self.get_model_fields()[key].get_default())

    def _decompose_class(self):
        cls = self.get_model_cls()
        if not cls.__config__.orm_mode:
            raise ConfigError('You must have the config attribute orm_mode=True for models of a ModelObject.')
        obj = cls._decompose_class(self)
        return cls, obj

    def model(self, force=False, validate=True, include=None):
        if validate:
            values, fields_set, validation_error = self.validate(include=include)
            if validation_error and not force:
                raise validation_error
            cls = self.get_model_cls()
            m = cls.__new__(cls)
            object.__setattr__(m, '__dict__', values)
            object.__setattr__(m, '__fields_set__', fields_set)
            return m
        else:
            cls, obj = self._decompose_class()
            return cls.construct(**{k: v for k, v in obj.items() if k in cls.__fields__})

    def validate(self, include=None):
        """
        Validate the current object.
        :param include: Only validate on given parameters
        :return:
        """
        cls, obj = self._decompose_class()

        # Disable validation for unneeded fields by deleting fields in a dummy class
        if include is not None:
            class ReducedClass(cls, BaseModel):
                pass

            cls = ReducedClass
            cls.__fields__ = {k: v for k, v in cls.__fields__.items() if k in include}
        # Todo stop supporting pydantic < 1.7
        if VERSION >= '1.7':
            defaults = {k: v.get_default() for k,v in cls.__fields__.items()}
        else:
            defaults = cls.__field_defaults__
        return validate_model(cls, {**deepcopy(defaults),
                                    **{k: obj[k] for k in obj.keys() if include is None or k in include}})

    def typed_id(self):
        cls = self.get_model_cls()
        if issubclass(cls, BaseStorageModel):
            return get_reference(self)
        else:
            raise Exception(f"Can't extract typed id: Model {str(cls)} is not an IdBasedEntry.")

    @classmethod
    def schema(cls):
        schema = cls.get_model_cls().schema()

        # Overwrite the model comment with the comment on the class if one exists
        if cls.__doc__ is not None:
            schema["description"] = cls.__doc__
        return schema

    @classmethod
    def store_schema(cls):
        if not cls._schema_reference:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            schema_repo = pads.schema_repository

            schema = cls.schema()
            schema_hash = persistent_hash(str(schema))
            if not schema_repo.has_object(uid=schema_hash):
                schema_obj = schema_repo.get_object(uid=schema_hash)
                # TODO store schema as string for now because $ is reserved in MongoDB
                schema_wrapper = {"category": "LoggerOutputSchema", "schema": str(jsonable_encoder(schema))}
                schema_obj.log_json(schema_wrapper)
            else:
                schema_obj = schema_repo.get_object(uid=schema_hash)
            cls._schema_reference = schema_obj.get_reference()
        return cls._schema_reference

    def json(self, force=True, validate=True, include=None, *args, **kwargs):
        model = self.model(force=force, validate=validate, include=include)
        if isinstance(model, ModelObject):
            return model.json(*args, force=force, validate=validate, include=include, **kwargs)
        return model.json(*args, include=include, **kwargs)

    def dict(self, force=True, validate=True, include=None, *args, **kwargs):
        model = self.model(force=force, validate=validate, include=include)
        if isinstance(model, ModelObject):
            return model.dict(*args, force=force, validate=validate, include=include, **kwargs)
        return model.dict(*args, include=include, **kwargs)


class ModelHolder(ModelInterface, metaclass=ABCMeta):
    """
    Used for objects storing their information directly into a validated base model
    """

    def __init__(self, *args, model: BaseStorageModel = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._model = self.get_model_cls()(**kwargs) if model is None else model

    def __getattr__(self, name):
        if name not in ["_model", "_model_cls"] and name in self.get_model_fields().keys():
            return getattr(self._model, name)
        else:
            return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name not in ["_model", "_model_cls"] and name in self.get_model_fields().keys():
            setattr(self._model, name, value)
        else:
            return object.__setattr__(self, name, value)

    def model(self):
        return self._model

    def validate(self):
        validate_model(self.get_model_cls(), self._model.__dict__)

    def schema(self):
        return self._model.schema()

    def json(self, *args, **kwargs):
        return self._model.json(*args, **kwargs)


class ModelErrorHandler:
    """ Class to handle errors on the validation of an validatable. """

    def __init__(self, absolute_path=None, validator=None, handle=None):
        self._absolute_path = absolute_path
        self._validator = validator
        self._handle = handle

    @property
    def validator(self):
        return self._validator

    @property
    def absolute_path(self):
        return self._absolute_path

    def handle(self, cls, e, options):
        if (not self._absolute_path or deque(self._absolute_path) == e.absolute_path) and (
                not self._validator or self.validator == e.validator):
            if self._handle is None:
                self._default_handle(e)
            else:
                return self._handle(cls, e, options)
        else:
            raise e

    def _default_handle(self, e):
        print("Empty validation handler triggered: " + str(self))
        raise e


class ModelFactory:

    @staticmethod
    def from_object(cls: BaseModel, obj, handlers: List[ModelErrorHandler] = None):
        return ModelFactory._try_creation(cls, cls.from_orm, handlers=handlers, __history=[], obj=obj)

    @staticmethod
    def make(cls, *args, handlers: List[ModelErrorHandler] = None, **options):
        return ModelFactory._try_creation(cls, cls, *args, handlers=handlers, __history=[], **options)

    @staticmethod
    def _try_creation(cls, fn, *args, handlers: List[ModelErrorHandler] = None, __history=None, **options):
        if handlers is None:
            handlers = []
        try:
            return fn(*args, **options)
        except ValidationError as e:
            # Raise error if we can't handle anything
            if handlers is None:
                raise e
            for handler in handlers:
                new_options = handler.handle(cls, e, options)
                # If the handler could fix the problem return the new value
                if new_options is not None and e not in __history and new_options not in __history:
                    __history.append(e)
                    __history.append(new_options)

                    # Try to create object again
                    return ModelFactory._try_creation(cls, handlers=handlers, __history=__history, **new_options)
            # Raise error if we fail
            raise e
