from logging import warning


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


class QualNameHook(Hook):
    """
    This class defines a pypads hook triggering if the function name equals the given name.
    """

    type = "qual_name"

    def __init__(self, event, name):
        super().__init__(event)
        self._name = name

    @property
    def name(self):
        """
        Function name to hook to
        :return:
        """
        return self._name

    def is_applicable(self, *args, fn=None, **kwargs):
        return fn is not None and fn.__name__ == self.name


class PackageNameHook(Hook):
    """
    This class defines a pypads hook triggering if the package name includes given name.
    """

    type = "package_name"

    def __init__(self, event, name):
        super().__init__(event)
        self._name = name

    @property
    def name(self):
        """
        Package name to hook to
        :return:
        """
        return self._name

    def is_applicable(self, *args, mapping=None, **kwargs):
        return mapping is not None and self.name in mapping.reference


def get_hooks(hook_map):
    hooks = []
    for event, hook_serialization in hook_map.items():
        if Hook.has_type_name(hook_serialization):
            hooks.append(Hook(event))
        else:
            for hook in hook_serialization:
                if isinstance(hook, Hook):
                    hooks.append(hook)
                elif hasattr(hook, 'type'):
                    if QualNameHook.has_type_name(hook['type']):
                        hooks.append(QualNameHook(event, hook['name']))

                    elif PackageNameHook.has_type_name(hook['type']):
                        hooks.append(PackageNameHook(event, hook['name']))
                    else:
                        warning("Type " + str(hook['type']) + " of hook " + str(hook) + " unknown.")
                else:
                    hooks.append(QualNameHook(event, hook))
    return hooks
