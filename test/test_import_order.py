from test.base_test import BaseTest, TEST_FOLDER


class PypadsImportOrder(BaseTest):

    def test_punch_before_import(self):
        from pypads.app.base import PyPads
        from test_classes.dummy_mapping import _get_punch_dummy_mapping
        tracker = PyPads(uri=TEST_FOLDER, mappings=_get_punch_dummy_mapping())
        tracker.activate_tracking(reload_modules=True)
        tracker.start_track()
        from test_classes.dummy_classes import PunchDummy
        from test_classes.dummy_classes import PunchDummy2
        dummy2 = PunchDummy2(2)
        assert hasattr(PunchDummy, "_pypads_mapping_PunchDummy")
        assert hasattr(PunchDummy2, "_pypads_mapping_PunchDummy2")
        assert hasattr(dummy2, "_pypads_mapping_PunchDummy2")

    def test_punch_after_import(self):
        from test_classes.dummy_classes import PunchDummy
        from test_classes.dummy_classes import PunchDummy2
        dummy2 = PunchDummy2(2)
        from pypads.app.base import PyPads
        from test_classes.dummy_mapping import _get_punch_dummy_mapping
        # TODO PunchDummy2 has PunchDummy as reference
        tracker = PyPads(uri=TEST_FOLDER, mappings=_get_punch_dummy_mapping())
        tracker.activate_tracking(reload_modules=True)
        tracker.start_track()
        from test_classes.dummy_classes import PunchDummy as a
        from test_classes.dummy_classes import PunchDummy2 as b
        assert not hasattr(a, "_pypads_mapping_PunchDummy")
        assert not hasattr(b, "_pypads_mapping_PunchDummy2")
        assert not hasattr(PunchDummy, "_pypads_mapping_PunchDummy")
        assert not hasattr(PunchDummy2, "_pypads_mapping_PunchDummy2")
        assert not hasattr(dummy2, "_pypads_mapping_PunchDummy2")

    def test_punch_after_import_clear_imports(self):
        from test_classes.dummy_classes import PunchDummy
        from test_classes.dummy_classes import PunchDummy2
        dummy2 = PunchDummy2(2)
        from pypads.app.base import PyPads
        from test_classes.dummy_mapping import _get_punch_dummy_mapping
        # TODO Punching of globals?
        tracker = PyPads(uri=TEST_FOLDER, mappings=_get_punch_dummy_mapping())
        tracker.activate_tracking(clear_imports=True, reload_modules=False)
        tracker.start_track()
        from test_classes.dummy_classes import PunchDummy as c
        from test_classes.dummy_classes import PunchDummy2 as d
        assert hasattr(c, "_pypads_mapping_PunchDummy")
        assert hasattr(d, "_pypads_mapping_PunchDummy2")
        assert not hasattr(PunchDummy, "_pypads_mapping_PunchDummy")
        assert not hasattr(PunchDummy2, "_pypads_mapping_PunchDummy2")
        assert not hasattr(dummy2, "_pypads_mapping_PunchDummy2")
