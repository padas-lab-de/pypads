class Parameter(object):
    """
    A class representing a single parameter, that was extracted using the ExperimentVisitor.
    It contains the extracted value and the path in the original object to that parameter.
    """

    def __init__(self, value, attributes):
        """
        Constructs a new Parameter.
        :param value: the value of the parameter
        :param attributes: A dictionary containing additional information to that Parameter
        """
        self.value = value
        self.attributes = attributes

    def type(self):
        """
        Returns the type of the value of the parameter.
        :return: the type of the value
        """
        return type(self.value)

    def __ne__(self, other):
        return self.value != other

    def __eq__(self, other):
        return self.value == other

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return "{ value: " + repr(self.value) + ", " + ", ".join(k + ": " + str(v) for k, v in self.attributes.items()) + " }"

    def __str__(self):
        return str(self.value)

