
import pytest
import ckan.plugins.toolkit as toolkit
from .conftest import can_show_validation_badge


@pytest.mark.parametrize(
    "is_sysadmin, can_package_update, expected",
    [
        (True, False, True),
        (False, True, True),
        (False, False, False),
    ],
)
def test_can_show_validation_badge(monkeypatch, is_sysadmin, can_package_update, expected):
    def fake_check_access(action, context=None, data_dict=None):
        if action == "sysadmin":
            return is_sysadmin

        if action == "package_update":
            assert data_dict == {"id": "dataset-1"}
            return can_package_update

        return False

    monkeypatch.setattr(toolkit, "check_access", fake_check_access)

    assert can_show_validation_badge("dataset-1") is expected
