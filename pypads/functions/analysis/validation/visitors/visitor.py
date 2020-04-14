"""
General visitors, that can be combined recursively to extract arbitrary data from any python object.
"""

import abc
import importlib
import inspect
from abc import abstractmethod

from .mappings import type_mappings
from .parameter import Parameter
from .schema import SchemaMismatch


class Visitor(abc.ABC):
    """
    The base class of any Visitor to inspect python objects and extract the setup information.
    For every value there will also be the access string of the item in the original object stored.
    """

    def __init__(self, schema=None):
        """
        Default implementation of constructor.
        :param schema: (optional) the expected schema of the extracted paramters
        """
        super().__init__()
        self.schema = schema

    def __call__(self, object, result=None, path=""):
        """
        Make a visitor callable. Calls extract, but also verifies if the result fits the provided schema, if any.
        :param object: see extract
        :param result: (optional) the output-dictionary
        :param path: (optional) the path to keep track of recursive calls
        :return: a tuple containing the result of extract and the schema of the visitor
        """
        if result is None:
            result = {}
        self.extract(object, result, path)
        if self.schema is not None:
            valid = self.schema.verify(result)
            if not valid[0]:
                raise SchemaMismatch(valid[1])
        return result, self.schema

    @abstractmethod
    def extract(self, object, result, path=""):
        """
        (abstract) Must be overridden by subclasses to implement custom extraction behaviour.
        :param object: the object of which information are to be extracted
        :param result: a dictionary containing all extracted information
        :param path: used to keep the path-information of the original item
        :return: a dictionary containing all extracted padre-keywords of the template
        """
        return

    @staticmethod
    def applyVisitor(object, result, template, path):
        """
        Applies the Visitor to the object depending on the type of template and stores the result in the result variable:
        - dict: the DictVisitor will be applied to the object using that dict as template
        - tuple: the TupleVisitor will be applied to the object using that tuple as template
        - str: the value of the object will be stored in the result dict using the value of the string as path in the result dict
        - callable: the template will get called with the object and a reference to the result-dictionary as arguments
        - None: no information will be extracted
        """
        if type(template) is str:
            elements = template.split(".")
            last_element = elements[-1]
            elements = elements[:-1]
            target_dict = result
            for e in elements:
                if not e in target_dict:
                    target_dict[e] = {}
                target_dict = target_dict[e]

            if last_element in target_dict:
                print("Warning: Parameter '" + template + "' extracted multiple times! Last value will be used.")
            target_dict[last_element] = Parameter(object, {"path": path})
        elif type(template) is dict:
            DictVisitor(template).extract(object, result, path)
        elif type(template) is tuple:
            TupleVisitor(template).extract(object, result, path)
        elif callable(template):
            template(object, result, path)
        elif template is None:
            pass
        else:
            raise TypeError("Template contains value of unexpected Type: " + str(type(template)))

        return result


class DictVisitor(Visitor):
    """
    A Visitor-implementation to inspect library-specific experiment setups and extract the setup information by using a template-dictionary.
    For each key in the dicitionary the corresponding value will be applied as visitor to a member of object by the same name as key.
    """

    def __init__(self, template, schema=None):
        """
        :param template: template dictionary describing the experiment hierarchy
        :param schema: (optional) the expected schema of the extracted paramters
        """
        super().__init__(schema)
        self.template = template

    def extract(self, object, result, path=""):
        """
        Implementation of the ExperimentVisitor-interface. Returns the result of a call to extract_rec with the given arguments and the stored template.
        :param object: the object of which information are to be extracted
        :param result: a dictionary containing all extracted information
        :param path: used to keep the path-information of the original item
        :return: a dictionary containing all extracted padre-keywords of the template
        """
        return DictVisitor.extract_rec(object, result, self.template, path)

    @staticmethod
    def extract_rec(object, result, template, path):
        """
        Stores all information of object extracted using template in the dict result.
        :param object: an object that is part of the experiment description
        :param result: result dictionary used for recursion
        :param template: template used for recursion
        :param path: used to keep the path-information of the original item
        :return: a dictionary containing all extracted padre-keywords of the template
        """
        # Check if object is a dict or a class object
        if type(object) is dict:
            getter = lambda k: object[k]
        elif hasattr(object, "__dict__"):
            getter = lambda k: getattr(object, k)
        else:
            raise TypeError("Inspected object has unsupported Type: " + str(type(object)))

        for k in template:
            Visitor.applyVisitor(getter(k), result, template[k], path + "." + k)
            # print("Warning: Parameter '" + k + "' could not be found in object " + repr(object) + ".")

        return result


class ListVisitor(Visitor):
    """
    A Visitor-implementation to inspect library-specific experiment setups and extract the setup information of a list by using a template on every object of the list.
    The template is represented by a dict, where a value can be of any of the types supported by ExperimentVisitor.applyVisitor.
    """

    def __init__(self, prefix, visitor, schema=None):
        """
        :param prefix: name, that is used to store the list of extracted values
        :param visitor: template visitor describing the hierarchy for the elements of the list
        :param schema: (optional) the expected schema of the extracted paramters
        """
        super().__init__(schema)
        self.prefix = prefix
        self.visitor = visitor

    def extract(self, object, result, path=""):
        """
        Implementation of the ExperimentVisitor-interface. Inserts the list of dictionaries,
         each obtained by calling applyVisitor on the respective element in the input list, into result with the key given by self.prefix.
        :param object: the input-list of which information are to be extracted
        :param result: a dictionary containing all extracted information
        :param path: used to keep the path-information of the original item
        :return: the result dictionary
        """
        if self.prefix in result:
            print("Warning: List '" + path + "." + self.prefix + "' extended by multiple runs.")
        else:
            result[self.prefix] = []
        result[self.prefix].extend(
            [self.applyVisitor(object[i], {}, self.visitor, path + "[" + str(i) + "]") for i in range(len(object))])
        return result


class TupleVisitor(Visitor):
    """
    A Visitor-implementation to inspect library-specific experiment setups and extract the setup information of a tuple-like by applying a template-tuple pairwise on the objects of the tuple.
    The template is represented by a tuple, where a value can be of any of the types supported by ExperimentVisitor.applyVisitor.
    """

    def __init__(self, visitors, schema=None):
        """
        :param visitors: template tuple describing the visitors for the elements in the input-tuple
        :param schema: (optional) the expected schema of the extracted paramters
        """
        super().__init__(schema)
        self.visitors = visitors

    def extract(self, object, result, path=""):
        """
        Implementation of the ExperimentVisitor-interface. Applies pairwise the template-visitor to the elements of the input-object.
        :param object: the input-tuple of which information are to be extracted
        :param result: a dictionary containing all extracted information
        :param path: used to keep the path-information of the original item
        :return: a dictionary containing all extracted padre-information
        """
        if len(object) != len(self.visitors):
            print("Warning: Tuple size doesn't match!")
        for i in range(min(len(object), len(self.visitors))):
            self.applyVisitor(object[i], result, self.visitors[i], path + "[" + str(i) + "]")
        return result


class SelectVisitor(Visitor):
    """
    A Visitor-implementation to inspect library-specific experiment setups and select the correct visitor using a decision-dict.
    The Dictionary contains pairs of classes and visitors. A visitor is selected if the object is an instance of the class.
    """

    def __init__(self, visitors, schema=None):
        """
        :param visitors: a dict, that maps base-classes to visitor-objects
        :param schema: (optional) the expected schema of the extracted paramters
        """
        super().__init__(schema)
        self.visitors = visitors

    def extract(self, object, result, path=""):
        """
        Implementation of the ExperimentVisitor-interface. Selects a visitor according to the base class of object. If no class matches the visitor to the key None is used, if available.
        :param object: the input-tuple of which information are to be extracted
        :param result: a dictionary containing all extracted information
        :param path: used to keep the path-information of the original item
        :return: a dictionary containing all extracted padre-information
        """
        visitor = None
        for k, v in self.visitors.items():
            if k:
                if isinstance(k, str):
                    splits = k.rsplit('.', 1)
                    module = importlib.import_module(splits[0])
                    k = getattr(module, splits[-1])
                if inspect.isclass(k) and isinstance(object, k):
                    visitor = v
                    break
        if visitor is None:
            if None in self.visitors:
                visitor = self.visitors[None]
        if visitor is None:
            raise TypeError("Unsupported object encountered: " + str(type(object)))
        return self.applyVisitor(object, result, visitor, path)


class CombineVisitor(Visitor):
    """
    A Visitor-implementation to combine multiple visitor-objects.
    """

    def __init__(self, visitors):
        """
        :param visitors: a list, containing all visitors
        :param schema: (optional) the expected schema of the extracted paramters
        """
        super().__init__()
        self.visitors = visitors

    def extract(self, object, result, path=""):
        """
        Implementation of the ExperimentVisitor-interface. Applies all visitors to object.
        :param object: the input-tuple of which information are to be extracted
        :param result: a dictionary containing all extracted information
        :param path: used to keep the path-information of the original item
        :return: a dictionary containing all extracted padre-information
        """
        for visitor in self.visitors:
            self.applyVisitor(object, result, visitor, path)
        return result


class ConstantVisitor(Visitor):
    """
    A Visitor-implementation that inserts a constant dict of values into the result-dict.
    """

    def __init__(self, values, schema=None):
        """
        :param values: the constant values
        :param schema: (optional) the expected schema of the extracted paramters
        """
        super().__init__(schema)
        self.values = values

    def extract(self, object, result, path=""):
        """
        Implementation of the ExperimentVisitor-interface. Adds the items in self.values to result.
        :param object: the input-tuple of which information are to be extracted
        :param result: a dictionary containing all extracted information
        :param path: used to keep the path-information of the original item
        :return: a dictionary containing all extracted padre-information
        """
        for k in self.values:
            self.applyVisitor(self.values[k], result, k, path)
        return result


class SubpathVisitor(Visitor):
    """
    A Visitor that creates and steps into a subpath of the result dict without changing object and applies its visitor on the object in the new path.
    """

    def __init__(self, subpath, visitor, schema=None):
        """
        :param subpath: the subpath to create
        :param visitor: the visitor
        :param schema: (optional) the expected schema of the extracted paramters
        """
        super().__init__(schema)
        self.subpath = subpath.split(".")
        self.visitor = visitor

    def extract(self, object, result, path=""):
        """
        Implementation of the ExperimentVisitor-interface. Creates its subpath in result and calls applyVisitor with its given visitor on object.
        If any element of the path ends with '[]', a list, which will be created if not existent in the subobject with the given key, will be appended a new dicitionary.
        otherwise the dicitonary will be inserted directly into the subobject, if not existing.
        :param object: the input-object to be passed directly to applyVisitor
        :param result: a dictionary containing all extracted information
        :param path: used to keep the path-information of the original item
        :return: a dictionary containing all extracted padre-information
        """
        subresult = result
        for s in self.subpath:
            if s.endswith("[]"):
                s = s[:-2]
                if s not in subresult:
                    subresult[s] = []
                subresult[s].append({})
                subresult = subresult[s][-1]
            else:
                if s not in subresult:
                    subresult[s] = {}
                subresult = subresult[s]

        return self.applyVisitor(object, subresult, self.visitor, path)


class AlgorithmVisitor(Visitor):
    """
    A Visitor that uses the information given in mapping.json to extract the information of an object.
    """

    def __init__(self, schema=None, param_additionalInformation=[]):
        """
        Creates a new AlgorithmVisitor.
        :param schema: (optional) the expected schema of the extracted paramters
        :param param_additionalInformation: (optional) set of keys to parameters, for which the respective values from mappings.py should be added to the results
        """
        super().__init__(schema)
        self.param_info = param_additionalInformation

    def setParamAdditionalInfo(self, param_additionalInformation):
        """
        Modifies the set of keys to parameters, for which the respective values from mappings.py should be added to the results.
        :param param_additionalInformation: the new set
        """
        self.param_info = param_additionalInformation

    def extract(self, object, result, path=""):
        """
        Implementation of the ExperimentVisitor-Interface. It looks for a mapping of the object-type to an algorithm.
        If there is none a ValueError is thrown. Otherwise all parameters of the algorithm will be extracted.
        :param object: the input-object to be passed directly to applyVisitor
        :param result: a dictionary containing all extracted information
        :param path: used to keep the path-information of the original item
        :return: a dictionary containing all extracted padre-information
        """

        fullName = "Unknown"
        for key, value in inspect.getmembers(object):
            if key.startswith("_pypads_mapping"):
                for mapping in value:
                    fullName = mapping.reference
                    break
                break
        fullName_ = object.__class__.__module__ + "." + object.__class__.__name__ if hasattr(object,
                                                                                             "__module__") else fullName
        if fullName_ in type_mappings:
            description, lib = type_mappings[fullName_]
        elif fullName != fullName_ and fullName in type_mappings:
            description, lib = type_mappings[fullName]
        else:
            raise ValueError("The algorithm described by class '" + fullName +"/" + fullName_ + "' is not registered!")

        result['algorithm'] = Parameter(description['name'], {"path": path})

        params = description.get('hyper_parameters', {})
        result['hyper_parameters'] = {}
        for param_type in params:
            param_list = {}
            result['hyper_parameters'][param_type] = param_list
            for param in params[param_type]:
                value = object.__dict__
                for k in param[lib]['path'].split('.'):
                    value = value[k]
                # resolve
                param_list[param['name']] = Parameter(value, {"path": path + "." + param[lib]['path'],
                                                              **{k: param[k] for k in self.param_info}})

        return result
