punch_dummy_mapping = {
    "default_hooks": {
        "modules": {
            "fns": {}
        },
        "classes": {
            "fns": {}
        },
        "fns": {}
    },
    "algorithms": [
        {
            "name": "punchtest",
            "other_names": [],
            "implementation": {
                "sklearn": "test_classes.dummy_classes"
            },
            "hooks": {
                "pypads_dummy_hook": "always"
            }
        }],
    "metadata": {
        "author": "Thomas Weißgerber",
        "library": "test_classes",
        "library_version": "0.0.1",
        "mapping_version": "0.1"
    }
}


def _get_punch_dummy_mapping():
    from pypads.autolog.mappings import MappingFile
    return MappingFile("punch_dummy", punch_dummy_mapping)
