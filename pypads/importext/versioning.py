import re
from typing import Type

from pydantic.main import BaseModel

from pypads.exceptions import VersionNotFoundException
from pypads.importext.semver import parse_constraint
from pypads.model.domain import LibSelectorModel
from pypads.model.metadata import ModelObject
from pypads.utils.util import is_package_available, find_package_version, find_package_regex_versions


class LibSelector(ModelObject):
    """
    Selector class holding version constraint and name of a library. @see poetry sem versioning
    """

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return LibSelectorModel

    def __init__(self, *args, name, regex=False, constraint: str = "*", specificity: int = None, **kwargs) -> None:
        super().__init__(*args, name=name, regex=regex, constraint=constraint,
                         specificity=specificity or self._calc_specificity(), **kwargs)
        self._parsed_constraint = parse_constraint(constraint)

    @staticmethod
    def from_dict(library):
        if library is None:
            return None
        return LibSelector(name=library["name"], constraint=library["version"])

    def _calc_specificity(self):
        """
        Calculates a value how specific the selector is. The more specific it is the higher the value is.
        TODO do some magic here.
        :return:
        """
        return 0

    def is_installed(self):
        """
        Check if a match is installed
        :return:
        """
        if self.regex:
            return any({self.allows(version) for version in find_package_regex_versions(self.name).values() if
                        version is not None})
        else:
            if is_package_available(self.name):
                version = find_package_version(self.name)
                if version is None:
                    raise VersionNotFoundException("Couldn't find version for lib {}".format(self.name))
                return self.allows(version)
            return False

    def allows_any(self, other):  # type: (LibSelector) -> bool
        """
        Check if the constraint overlaps with another constaint.
        :param other:
        :return:
        """
        return re.compile(self.name).match(other.name) and self._parsed_constraint.allows_any(other._parsed_constraint)

    def allows(self, version):  # type: ("Version") -> bool
        """
        Check if the constraint allows given version number.
        :param version:
        :return:
        """
        from pypads.importext.semver import Version
        return self._parsed_constraint.allows(Version.parse(version))

    def __str__(self):
        return "LibSelector[name=" + self.name + "," + self.constraint + "]"


all_libs = LibSelector(name=".*", constraint="*")
