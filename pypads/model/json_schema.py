# import re
# from typing import Sequence
#
# from jsonschema import ValidationError, validators
#
#
# # TODO move defaults to json schema
# # def extend_with_default(validator_class):
# #     # see https://python-jsonschema.readthedocs.io/en/stable/faq/
# #     validate_properties = validator_class.VALIDATORS["properties"]
# #
# #     def set_defaults(validator, properties, instance, schema):
# #         for property, subschema in properties.items():
# #             if "default" in subschema:
# #                 instance.setdefault(property, subschema["default"])
# #
# #         for error in validate_properties(
# #                 validator, properties, instance, schema,
# #         ):
# #             yield error
# #
# #     return validators.extend(
# #         validator_class, {"properties": set_defaults},
# #     )
# from pypads.model.validation import ValidationErrorHandler
#
#
# # def padre_enum(validator, padre_enum, instance, schema):
# #     """
# #     Function to evaluate if a enum exists via jsonschema evaluation. This is used for ontology validation.
# #     :param validator:
# #     :param padre_enum:
# #     :param instance:
# #     :return:
# #     """
# #     if validator.is_type(instance, "string"):
# #         if padre_enum is not None:
# #             # noinspection PyProtectedMember
# #             if not hasattr(PaDREOntology, padre_enum):
# #                 yield ValidationError("%r is not a valid padre enum" % (padre_enum))
# #             # TODO cleanup access to enum
# #             elif instance not in getattr(PaDREOntology, padre_enum)._value2member_map_:
# #                 yield ValidationError("%r is not a valid value entry of padre enum %r" % (instance, padre_enum))
#
#
# padre_schema_validator = validators.extend(validators.Draft7Validator,
#                                            validators={"padre_enum": padre_enum}, version="1.0")
#
#
# class JsonSchemaRequiredHandler(ValidationErrorHandler):
#     """
#     Handle a required error of jsonschema validation.
#     """
#
#     def __init__(self, absolute_path=None, validator=None, get_value=None):
#         super().__init__(absolute_path, validator, get_value)
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
#         return self.update_options(e, options, super().handle(obj, e, options))
#
#     @staticmethod
#     def update_options(e, options, value):
#         deq = e.absolute_path
#         new = {}
#         current_level = new
#
#         # Build path for the options dict
#         while len(deq) > 0:
#             val = deq.popleft()
#             if len(deq) != 0:
#                 current_level[val] = {}
#                 current_level = current_level[val]
#
#         # Insert value in correct field in options dict
#         if _seq_but_not_str(e.validator_value):
#             for key in e.validator_value:
#
#                 # TODO parsing the jsonschema errors is really ugly there has to be a better way (Own Validator?)
#                 match = re.compile("'(" + re.escape(key) + ")'.*").match(e.message)
#                 if match is not None:
#                     key = match.group(1)
#                     current_level[key] = value
#                     break
#         return {**options, **new}
#
#
# def _seq_but_not_str(obj):
#     return isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray))
