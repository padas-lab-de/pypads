# from abc import ABCMeta, abstractmethod
# from collections.__init__ import deque
# from typing import List
#
# from jsonschema import ValidationError
#
#
# # noinspection PyUnusedLocal,PyShadowingNames,PyProtectedMember
# from pypads import logger
#
#
# class ValidateableMixin:
#     __metaclass__ = ABCMeta
#     """ This class implements basic logic for validating the state of it's input parameters """
#
#     # noinspection PyBroadException
#     def __init__(self, *args, metadata, validate=True, **kwargs):
#         super().__init__(*args, **kwargs)
#
#         if validate:
#             self.validate(metadata=metadata, **kwargs)
#
#     @abstractmethod
#     def validate(self, **kwargs):
#         raise NotImplementedError()
#
#     @abstractmethod
#     def dirty(self):
#         raise NotImplementedError()
#
#
# class ValidateParameterMixin:
#
#     def __init__(self, *args, **kwargs):
#         self._parameter_schema = kwargs.pop('parameter_schema', None)
#         super().__init__(args, kwargs)
#
#     def _validate_parameters(self, parameters):
#         if self._parameter_schema is None:
#             logger.warning(
#                 "A parameterized component needs a schema to validate parameters on execution time. Component: " + str(
#                     self) + " Parameters: " + str(parameters))
#         else:
#             # TODO validate if the parameters are according to the schema.
#             pass
#
#     @property
#     def parameter_schema(self):
#         return self._parameter_schema
#
#
# class ValidationErrorHandler:
#     """ Class to handle errors on the validation of an validatable. """
#
#     def __init__(self, absolute_path=None, validator=None, handle=None):
#         self._absolute_path = absolute_path
#         self._validator = validator
#         self._handle = handle
#
#     @property
#     def validator(self):
#         return self._validator
#
#     @property
#     def absolute_path(self):
#         return self._absolute_path
#
#     def handle(self, obj, e, options):
#         if (not self._absolute_path or deque(self._absolute_path) == e.absolute_path) and (
#                 not self._validator or self.validator == e.validator):
#             if self._handle is None:
#                 self._default_handle(e)
#             else:
#                 return self._handle(obj, e, options)
#         else:
#             raise e
#
#     def _default_handle(self, e):
#         print("Empty validation handler triggered: " + str(self))
#         raise e
#
#
# class ValidateableFactory:
#
#     @staticmethod
#     def make(cls, *args, handlers=List[ValidationErrorHandler], **options):
#         return ValidateableFactory._make(cls, *args, handlers=handlers, history=[], **options)
#
#     @staticmethod
#     def _make(cls, *args, handlers=List[ValidationErrorHandler], history=None, **options):
#         try:
#             return cls(*args, **options)
#         except ValidationError as e:
#             # Raise error if we can't handle anything
#             if handlers is None:
#                 raise e
#             for handler in handlers:
#                 new_options = handler.handle(cls, e, options)
#                 # If the handler could fix the problem return the new value
#                 if new_options is not None and e not in history and new_options not in history:
#                     history.append(e)
#                     history.append(new_options)
#
#                     # Try to create object again
#                     return ValidateableFactory._make(cls, handlers=handlers, history=history, **new_options)
#             # Raise error if we fail
#             raise e
