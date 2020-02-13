from logging import warning

from .mappings import name_mappings
from .parameter import Parameter


class SchemaMismatch(Exception):
    """Exception for schema-mismatch

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class Attribute(object):
    """
    Contains the following information about one attribute in a schema:
        the name,
        the type,
        a flag indicating if the attribute is optional and
        a description
    of the attribute
    """
    def __init__(self, name, desc, optional, type):
        """
        Sets up the information.
        :param name: the name of the attribute
        :param desc: the description of the attribute
        :param optional: indicating if the attribute is optional
        :param type: the type of the attribute
        """
        self.name = name
        self.type = type
        self.optional = optional
        self.desc = desc


class ListAttribute(Attribute):
    """
    An attribute with the type list, that contains a recursive schema to test the lists elements
    """
    def __init__(self, name, desc, optional, schema):
        """
        Sets up the information
        :param name: the name of the attribute
        :param desc: the description of the attribute
        :param optional: indicating if the attribute is optional
        :param schema: the recursive schema
        """
        super().__init__(name, desc, optional, list)
        self.schema = schema

    def verify(self, data, path, keyset):
        """
        Verifies all its elements using self.schema.
        :param exp_schema: the toplevel schema object
        :param data: the list to verify
        :param path: used for recursion. Used for readable error messages.
        :param keyset: used for recursion. Contains the unchecked keys of the data.
        :return: (bool, str) (True, ""), if the data fits. (False, <reason>), otherwise.
        """
        for i in range(len(data)):
            tmp = Schema.verify_static(data[i], self.schema, path + "[" + str(i) + "]")
            if not tmp[0]:
                return tmp
        return (True, "")


class DictAttribute(Attribute):
    """
    An attribute with the type dict, that contains a recursive schema to test the dicts elements
    """

    def __init__(self, schema, name="", desc="", optional=False):
        """
        Sets up the information
        :param schema: the recursive schema
        :param name: the name of the attribute, default=""
        :param desc: the description of the attribute, default=""
        :param optional: indicating if the attribute is optional, default=False
        """
        super().__init__(name, desc, optional, list)
        self.schema = schema

    def verify(self, data, path, keyset):
        """
        Verifies all its elements using self.schema.
        :param data: the list to verify
        :param path: used for recursion. Used for readable error messages.
        :param keyset: used for recursion. Contains the unchecked keys of the data.
        :return: (bool, str) (True, ""), if the data fits. (False, <reason>), otherwise.
        """

        for k in self.schema:
            p = path + "." + k
            if k in data:

                tmp = Schema.verify_static(data[k], self.schema[k], p)
                if not tmp[0]:
                    return tmp
                keyset.remove(k)

            elif not self.schema[k].optional:
                return (False, "Missing Parameter '" + p + "'.")

        return (True, "")


class SelectSchema(object):
    """
    A schema object, that has a decision function to get the correct schema for the dict and verifies it.
    """

    def __init__(self, decision):
        """
        Sets up the decision function
        :param decision: a decision function, that takes a dict and returns a schema dictionary
        """
        self.decision = decision

    def verify(self, data, path, keyset):
        """
        Verifies all its elements using self.schema.
        :param data: the list to verify
        :param path: used for recursion. Used for readable error messages.
        :param keyset: used for recursion. Contains the unchecked keys of the data.
        :return: (bool, str) (True, ""), if the data fits. (False, <reason>), otherwise.
        """
        return Schema.verify_static(data, self.decision(data), path, keyset)


class CombineSchemata(object):
    """
    A schema object, that contains a list of schema-objects, which are all verified against the data.
    """

    def __init__(self, schemata):
        """
        Sets up the decision function
        :param decision: a decision function, that takes a dict and returns a schema dictionary
        """
        self.schemata = schemata

    def verify(self, data, path, keyset):
        """
        Verifies the data using self.schemata.
        :param data: the data to verify
        :param path: used for recursion. Used for readable error messages.
        :param keyset: used for recursion. Contains the unchecked keys of the data.
        :return: (bool, str) (True, ""), if the data fits. (False, <reason>), otherwise.
        """
        for schema in self.schemata:
            tmp = Schema.verify_static(data, schema, path, keyset)
            if not tmp[0]:
                return tmp
        return (True, "")


class Schema(object):
    """
    Describing a schema for experiment parameters.
    """

    def __init__(self, schema):
        """
        constructs the schema with a schema object.
        :param schema: the object describing the schema.
        """
        self.schema = schema

    def verify(self, data):
        """
        Calls ExperimentVisitor.verify_static(data, self.schema).
        :param data: the data to be verified.
        :return: the result of the call to verify_static.
        """
        return Schema.verify_static(data, self.schema)

    @staticmethod
    def verify_static(data, schema, path="", keyset=None):
        """
        Verifies that the given data fits into the defined schema.
        :param data: the data to be checked
        :param schema: the schema to be checked against.
        :param keyset: used for warning-prompts. Contains all unchecked keys. If None it will be created from data
        :param path: (optional) used for recursion. Used for readable error messages.
        :return: (bool, str) (True, ""), if the data fits. (False, <reason-str>), otherwise.
        """

        if keyset is None:
            keyset_was_none = True
            if type(data) is dict:
                keyset = list(data.keys())
            else:
                keyset = []
        else:
            keyset_was_none = False

        if type(data) is list:
            if type(schema) is ListAttribute:
                tmp = schema.verify(data, path, keyset)
            else:
                return (False, "Parameter '" + path + "' has to be of type " + str(
                    schema.type) + " but is of type " + str(list) + ".")

            if not tmp[0]:
                return tmp
        elif type(data) is dict:
            if type(schema) in [SelectSchema, AlgorithmSchema]:
                tmp = schema.verify(data, path, keyset)
            elif type(schema) is dict:
                tmp = DictAttribute(schema).verify(data, path, keyset)
            elif type(schema) is list:
                tmp = CombineSchemata(schema).verify(data, path, keyset)
            elif type(schema) is DictAttribute:
                tmp = schema.verify(data, path, keyset)
            else:
                return (False, "Parameter '" + path + "' has to be of type " + str(
                    schema.type) + " but is of type " + str(dict) + ".")
            if not tmp[0]:
                return tmp
        elif type(data) is Parameter:
            if data.type() is not schema.type:
                return (False,
                        "Parameter '" + path + "' has to be of type " + str(schema.type) + " but is of type " + str(
                            data.type()) + ".")
        else:
            return (False, "Parameter '" + path + "' has unsupported type " + str(type(data)) + ".")

        if keyset_was_none:
            for l in keyset:
                warning("Warning: Attribute '" + path + "." + l + "' is not part of the schema.")

        return (True, "")


class AlgorithmSchema(object):
    """
    Describing the schema for an algorithm given the description in 'mappings.json'.
    """

    def verify(self, data, path, keyset):
        """
        Verifies that data fits the
        :param data: the data to be verified.
        :return: (bool, str) (True, ""), if the data fits. (False, <reason-str>), otherwise.
        """

        if not 'hyper_parameters' in data:
            return (False, "Missing 'hyper_parameters'-field!")

        alg = name_mappings[data['algorithm']]

        for param_type in alg['hyper_parameters']:
            if not param_type in data['hyper_parameters']:
                return (False, "Missing parameter-set '" + param_type + "'!")
            for param in alg['hyper_parameters'][param_type]:
                if not param['name'] in data['hyper_parameters'][param_type]:
                    return (False, "Missing parameter '" + param['name'] + "'!")


        keyset.remove('hyper_parameters')

        return (True, "")
