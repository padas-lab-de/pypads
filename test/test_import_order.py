import pytest

from test.base_test import BaseTest, TEST_FOLDER


class PypadsImportOrder(BaseTest):

    @pytest.mark.forked
    def test_punch_before_import(self):
        from pypads.base import PyPads
        from test_classes.dummy_mapping import _get_punch_dummy_mapping
        tracker = PyPads(uri=TEST_FOLDER, mapping=_get_punch_dummy_mapping(), reload_modules=True)
        from test_classes.dummy_classes import PunchDummy
        from test_classes.dummy_classes import PunchDummy2
        dummy2 = PunchDummy2(2)
        assert hasattr(PunchDummy, "_pypads_mapping_PunchDummy")
        assert hasattr(PunchDummy2, "_pypads_mapping_PunchDummy2")
        assert hasattr(dummy2, "_pypads_mapping_PunchDummy2")

    @pytest.mark.forked
    def test_punch_after_import(self):
        from test_classes.dummy_classes import PunchDummy
        from test_classes.dummy_classes import PunchDummy2
        dummy2 = PunchDummy2(2)
        from pypads.base import PyPads
        from test_classes.dummy_mapping import _get_punch_dummy_mapping
        # TODO PunchDummy2 has PunchDummy as reference
        tracker = PyPads(uri=TEST_FOLDER, mapping=_get_punch_dummy_mapping(), reload_modules=True)
        from test_classes.dummy_classes import PunchDummy as a
        from test_classes.dummy_classes import PunchDummy2 as b
        assert not hasattr(a, "_pypads_mapping_PunchDummy")
        assert not hasattr(b, "_pypads_mapping_PunchDummy2")
        assert not hasattr(PunchDummy, "_pypads_mapping_PunchDummy")
        assert not hasattr(PunchDummy2, "_pypads_mapping_PunchDummy2")
        assert not hasattr(dummy2, "_pypads_mapping_PunchDummy2")

    @pytest.mark.forked
    def test_punch_after_import_clear_imports(self):
        from test_classes.dummy_classes import PunchDummy
        from test_classes.dummy_classes import PunchDummy2
        dummy2 = PunchDummy2(2)
        from pypads.base import PyPads
        from test_classes.dummy_mapping import _get_punch_dummy_mapping
        # TODO Punching of globals?
        tracker = PyPads(uri=TEST_FOLDER, mapping=_get_punch_dummy_mapping(), clear_imports=True, reload_modules=False)
        from test_classes.dummy_classes import PunchDummy as c
        from test_classes.dummy_classes import PunchDummy2 as d
        assert hasattr(c, "_pypads_mapping_PunchDummy")
        assert hasattr(d, "_pypads_mapping_PunchDummy2")
        assert not hasattr(PunchDummy, "_pypads_mapping_PunchDummy")
        assert not hasattr(PunchDummy2, "_pypads_mapping_PunchDummy2")
        assert not hasattr(dummy2, "_pypads_mapping_PunchDummy2")
