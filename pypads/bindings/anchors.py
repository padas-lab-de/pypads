from pypads import logger

anchors = {}


class Anchor:
    """
    Class defining a name, description etc. on which a hook is based.
    """

    def __init__(self, name, description):
        """
        Constructor for an anchor.
        :param name: Name of the anchor.
        :param description: String describing the anchor and its purpose.
        """
        self._name = name
        self._description = description
        if self._name in anchors:
            logger.warning("Anchor with name {} already exists".format(self._name))
            pass
        anchors[self._name] = self

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        """
        Return a string describing the anchor and its purpose.
        :return:
        """
        return self._description

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __str__(self):
        return self._name


def init_anchors():
    if not all([a.name in anchors for a in DEFAULT_ANCHORS]):
        raise Exception("There seems to be an issues with adding the anchors")


def get_anchor(anchor):
    if isinstance(anchor, Anchor):
        return anchor
    if anchor not in anchors.keys():
        return None
    return anchors.get(anchor)


# TODO maybe change to enum
DEFAULT_ANCHORS = [Anchor("pypads_init", "Used if a tracked concept is initialized."),
                   Anchor("pypads_fit", "Used if an model is fitted to data."),
                   Anchor("pypads_predict", "Used if an model predicts something."),
                   Anchor("pypads_metric", "Used if an metric is compiled."),
                   Anchor("pypads_log", "Used to only log a call."),
                   Anchor("pypads_import", "Used for on-import logging")]

init_anchors()
