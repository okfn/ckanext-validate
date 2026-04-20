
import pytest
import ckan.plugins.toolkit as toolkit


def can_show_validation_controls(package_id):
    """
    Replica la regla actual de los templates:
    mostrar badges / botón Validate si es sysadmin
    o si tiene package_update sobre el dataset.
    """
    return (
        toolkit.check_access("sysadmin", {}, {})
        or toolkit.check_access("package_update", {}, {"id": package_id})
    )


@pytest.mark.parametrize(
    "is_sysadmin, can_package_update, expected",
    [
        (True, True, True),
        (True, False, True),
        (False, True, True),
        (False, False, False),
    ],
)
def test_can_show_validation_controls(monkeypatch, is_sysadmin, can_package_update, expected):
    calls = []

    def fake_check_access(action, context=None, data_dict=None):
        calls.append((action, context, data_dict))

        if action == "sysadmin":
            return is_sysadmin

        if action == "package_update":
            assert data_dict == {"id": "dataset-1"}
            return can_package_update

        return False

    monkeypatch.setattr(toolkit, "check_access", fake_check_access)

    assert can_show_validation_controls("dataset-1") is expected

    # Verifica el short-circuit: si ya es sysadmin, no debería consultar package_update
    if is_sysadmin:
        assert calls == [("sysadmin", {}, {})]
    else:
        assert calls == [
            ("sysadmin", {}, {}),
            ("package_update", {}, {"id": "dataset-1"}),
        ]
