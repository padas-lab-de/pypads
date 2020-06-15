import re
from abc import ABCMeta, abstractmethod

import yaml


class PackagePathSegment:
    """
    Single segment of a package path. This would be "module", "foo", "bar" in module.foo.bar
    """

    def __init__(self, content: str):
        self._content = content

    @property
    def content(self):
        return self._content

    def __hash__(self):
        return hash(self.content)

    def __eq__(self, other):
        return self._content == other.content

    def __str__(self):
        return str(self._content)


class PackagePath:
    """
    Full package path holding all needed segments.
    """

    def __init__(self, content):
        """
        :param content: Takes either a package name like "module.foo.bar" or a list of segments
        """
        if content is None:
            self._segments = []
        else:
            if isinstance(content, str):
                content = self.to_segments(content)
            if not isinstance(content, list):
                raise ValueError("PackagePath has to hold a list of PathSegments.")
            self._segments = content

    @staticmethod
    def to_segments(package):
        """
        Converts given package into segments
        :param package: Package name in form of "module.foo.bar"
        :return: Segments of package name
        """
        return [PackagePathSegment(s) for s in filter(lambda s: len(s) > 0, package.split("."))]

    @property
    def segments(self):
        """
        Returns all segments of the path
        :return:
        """
        return self._segments

    def __eq__(self, other):
        return len(self._segments) is len(other.segments) and all(
            [s == other.segments[i] for i, s in enumerate(self._segments)])

    def __hash__(self):
        return hash(tuple(hash(segment) for segment in self._segments))

    def __str__(self):
        return ".".join([str(s) for s in self.segments])

    def __add__(self, other):
        if isinstance(other, PackagePath):
            return PackagePath(self._segments + other.segments)
        elif isinstance(other, PackagePathSegment):
            copy = self._segments.copy()
            copy.append(other)
            return PackagePath(copy)
        elif isinstance(other, str):
            copy = self._segments.copy()
            copy.append(self.to_segments(other))
            return PackagePath(copy)


class SerializableMatcher:

    @staticmethod
    @abstractmethod
    def yaml_representer(dumper, data):
        """
        A yaml representer which can be used to dump a matcher to yaml
        :param dumper: yaml dumper
        :param data: data of the matcher to dump
        :return:
        """
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def yaml_constructor(loader, node):
        """
        A yaml constructor to build a model from a yaml entry
        :param loader: yaml loader
        :param node: the node in the yaml
        :return:
        """
        raise NotImplementedError()

    @staticmethod
    def unserialize(reference):
        """
        Function to unserialize a matcher from string
        :param reference: String serialization
        :return: Matcher object
        """
        raise NotImplementedError()

    @abstractmethod
    def serialize(self) -> str:
        """
        Function to simply serialize the matcher to string
        :return:
        """
        raise NotImplementedError()


class ISegmentMatcher(SerializableMatcher):
    """
    Matcher used to match a package path. This class is used to define mappings.
    """
    __metaclass__ = ABCMeta

    def __init__(self, content):
        """
        :param content: Content of the matcher. This can be everything used in the matches function.
        """
        self._content = content

    @property
    def content(self):
        """
        :return: Content of the matcher
        """
        return self._content

    @abstractmethod
    def matches(self, segment: PackagePathSegment):
        """
        Function used to check if a path segment matches the matcher
        :param segment:
        :return:
        """
        raise NotImplementedError()

    def __hash__(self):
        return hash(self.content)

    def __str__(self):
        return self.serialize()


class StaticMatcher(ISegmentMatcher):
    """
    Matcher to directly match paths via string comparision
    """
    TAG = u'tag:yaml.org,2002:python/sSeg'

    @staticmethod
    def unserialize(reference) -> ISegmentMatcher:
        return StaticMatcher(reference)

    @staticmethod
    def yaml_representer(dumper, data):
        return dumper.represent_scalar(StaticMatcher.TAG, "%s" % data.conent)

    @staticmethod
    def yaml_constructor(loader, node):
        return StaticMatcher(loader.construct_scalar(node))

    def matches(self, segment: PackagePathSegment):
        return segment.content == self.content

    def serialize(self):
        return self.content


class RegexMatcher(ISegmentMatcher):
    """
    Matcher to use regex to match the given path segment.
    """
    TAG = u'tag:yaml.org,2002:python/rSeg'

    @staticmethod
    def unserialize(reference) -> ISegmentMatcher:
        return RegexMatcher(reference[4:-1])

    @staticmethod
    def yaml_representer(dumper, data):
        return dumper.represent_scalar(RegexMatcher.TAG, "%s" % data.conent)

    @staticmethod
    def yaml_constructor(loader, node):
        return RegexMatcher(loader.construct_scalar(node))

    def matches(self, segment: PackagePathSegment):
        return re.match(self.content, segment.content)

    def serialize(self):
        return "{re:" + self.content + "}"


class PackagePathMatcher(SerializableMatcher):
    """
    Matcher checking a complete path with multiple other matchers.
    """
    TAG = u'tag:yaml.org,2002:python/pPath'

    def __init__(self, content):
        if isinstance(content, str):
            content = self.to_matchers(content)
        self._matchers = content

    @property
    def matchers(self):
        """
        :return: SegmentMatchers of the PathMatcher
        """
        return self._matchers

    @staticmethod
    def unserialize(reference):
        return PackagePathMatcher(PackagePathMatcher.to_matchers(reference))

    @staticmethod
    def to_matchers(reference):
        """
        Convert a full reference string to multiple matchers "module.{re:foo}.bar" converts to static, regex, static
        :param reference:
        :return:
        """
        matchers = []
        for matcher_content in filter(lambda s: len(s) > 0, re.split(r"({.*?\})", reference)):
            if matcher_content.startswith("{re:"):
                matchers.append(RegexMatcher.unserialize(matcher_content))
            else:
                c: str
                matchers = matchers + [StaticMatcher.unserialize(c) for c in
                                       filter(lambda s: len(s) > 0, matcher_content.split("."))]
        return matchers

    @staticmethod
    def yaml_representer(dumper, data):
        return dumper.represent_scalar(PackagePathMatcher.TAG, "%s" % data.serialize())

    @staticmethod
    def yaml_constructor(loader, node):
        return PackagePathMatcher(loader.construct_scalar(node))

    def matches(self, package_path: PackagePath):
        return all([m.matches(package_path.segments[i]) for i, m in enumerate(self._matchers) if
                    i < len(package_path.segments)])

    def full_match(self, package_path: PackagePath):
        return len(self._matchers) == len(package_path.segments) and all(
            [m.matches(package_path.segments[i]) for i, m in enumerate(self._matchers)])

    def serialize(self):
        return ".".join([m.serialize() for m in self.matchers])

    def __add__(self, other):
        if isinstance(other, PackagePathMatcher):
            return PackagePathMatcher(self.matchers + other.matchers)
        elif isinstance(other, ISegmentMatcher):
            copy = self.matchers.copy()
            copy.append(other)
            return PackagePathMatcher(copy)
        elif isinstance(other, str):
            copy = self.matchers.copy()
            copy.append(self.to_matchers(other))
            return PackagePath(copy)


# Register yaml constructors for easy direct translation
yaml.add_constructor(StaticMatcher.TAG, StaticMatcher.yaml_constructor, Loader=yaml.SafeLoader)
yaml.add_constructor(RegexMatcher.TAG, RegexMatcher.yaml_constructor, Loader=yaml.SafeLoader)
yaml.add_constructor(PackagePathMatcher.TAG, PackagePathMatcher.yaml_constructor, Loader=yaml.SafeLoader)
yaml.add_representer(StaticMatcher, StaticMatcher.yaml_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(RegexMatcher, RegexMatcher.yaml_representer, Dumper=yaml.SafeDumper)
yaml.add_representer(PackagePathMatcher, PackagePathMatcher.yaml_representer, Dumper=yaml.SafeDumper)
