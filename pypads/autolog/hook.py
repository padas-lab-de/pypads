import re
from _py_abc import ABCMeta
from abc import abstractmethod
from logging import warning, error


class Hook:
    """
    This class defines a pypads hook. This hook always triggers. Hooks are injected into function calls to inject different functionality.
    """

    type = "always"

    def __init__(self, event):
        self._event = event

    @property
    def event(self):
        """
        Event to trigger on hook execution
        :return:
        """
        return self._event

    @classmethod
    def has_type_name(cls, type):
        return cls.type == type

    def is_applicable(self, *args, **kwargs):
        return True


class RegexHook(Hook):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, event, regex):
        super().__init__(event)
        try:
            self._regex = re.compile(regex)
        except Exception as e:
            error("Couldn't compile regex: " + str(regex) + "of hook" + str(self) + ". Disabling it.")
            # Regex to never match anything
            self._regex = re.compile('a^')

    @property
    def regex(self):
        """
        Function name to hook to
        :return:
        """
        return self._regex


class QualNameHook(RegexHook):
    """
    This class defines a pypads hook triggering if the function name equals the given name.
    """

    def __init__(self, event, regex):
        super().__init__(event, regex)

    type = "qual_name"

    def is_applicable(self, *args, fn=None, **kwargs):
        return fn is not None and hasattr(fn, "__name__") and self.regex.match(fn.__name__)


class PackageNameHook(RegexHook):
    """
    This class defines a pypads hook triggering if the package name includes given name.
    """

    def __init__(self, event, regex):
        super().__init__(event, regex)

    type = "package_name"

    def is_applicable(self, *args, mapping=None, **kwargs):
        return mapping is not None and self.regex.match(mapping.reference)


def get_hooks(hook_map):
    """
    This function returns hook objects defined in a mapping.
    :param hook_map: mapping containing the hooks
    :return:
    """
    hooks = []
    for event, hook_serialization in hook_map.items():
        if Hook.has_type_name(hook_serialization):
            # If we are a string "always"
            hooks.append(Hook(event))
        else:
            for hook in hook_serialization:
                # If hook is already a hook
                if isinstance(hook, Hook):
                    hooks.append(hook)

                # If hook dict has a type
                elif hasattr(hook, 'type'):
                    if QualNameHook.has_type_name(hook['type']):
                        hooks.append(QualNameHook(event, hook['regex']))
                    elif PackageNameHook.has_type_name(hook['type']):
                        hooks.append(PackageNameHook(event, hook['regex']))
                    else:
                        warning("Type " + str(hook['type']) + " of hook " + str(hook) + " unknown.")

                # If hook is just a string
                else:
                    hooks.append(QualNameHook(event, hook))
    return hooks


def make_hook_applicable_filter(hook, ctx, mapping):
    """
    Create a filter to check if hook is applicable
    :param hook:
    :param ctx:
    :param mapping:
    :return:
    """

    def hook_applicable_filter(name):
        if hasattr(ctx, name):
            if not name.startswith("__") or name == "__init__":
                if not name.startswith("_pypads"):
                    try:
                        fn = getattr(ctx, name)
                        return hook.is_applicable(mapping=mapping, fn=fn)
                    except RecursionError as re:
                        error("Recursion error on '" + str(
                            ctx) + "'. This might be because __get_attr__ is being wrapped. " + str(re))
                else:
                    pass
                    # debug("Tried to wrap pypads function '" + name + "' on '" + str(ctx) + "'. Omit logging.")
            else:
                pass
                # debug(
                #     "Tried to wrap non-constructor native function '" + name + "' on '" + str(ctx) + "'. Omit logging.")
        else:
            warning("Can't access attribute '" + str(name) + "' on '" + str(ctx) + "'. Skipping.")
        return False

    return hook_applicable_filter


def find_applicable_hooks(context, mapping):
    if mapping.hooks:
        for hook in mapping.hooks:
            for name in list(filter(make_hook_applicable_filter(hook, context, mapping), dir(context))):
                yield name, context, mapping
