from pypads.autolog.mappings import SerializedMapping

punch_dummy_mapping = """
metadata:
  author: "Thomas Weißgerber"
  version: "0.0.1"
  library:
    name: "test_classes"
    version: "0.1"

mappings:
    :test_classes.dummy_classes.{re:.*}:
            events: "pypads_dummy_hook"
"""


def _get_punch_dummy_mapping():
    return SerializedMapping("punch_dummy", punch_dummy_mapping)
