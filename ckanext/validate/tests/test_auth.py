from ckan.plugins import toolkit

from ckanext.validate.auth import validation as validate_auth


def test_resource_validate_auth_checks_resource_update(monkeypatch):
    captured = {}

    def fake_check_access(name, context, data_dict):
        captured.update({"name": name, "context": context, "data_dict": data_dict})

    monkeypatch.setattr(validate_auth.toolkit, "check_access", fake_check_access)

    username = "alice"
    result = validate_auth.resource_validate({"user": username}, {"id": "res-1"})

    assert result == {"success": True}
    assert captured == {
        "name": "resource_update",
        "context": {"user": username},
        "data_dict": {"id": "res-1"},
    }


def test_resource_validate_auth_returns_false_when_unauthorized(monkeypatch):
    def fake_check_access(name, context, data_dict):
        raise toolkit.NotAuthorized()

    monkeypatch.setattr(validate_auth.toolkit, "check_access", fake_check_access)

    result = validate_auth.resource_validate({}, {"id": "res-1"})

    assert result == {
        "success": False,
        "msg": "Not authorized to validate this resource",
    }


def test_resource_validation_show_auth_checks_resource_show(monkeypatch):
    captured = {}

    def fake_check_access(name, context, data_dict):
        captured.update({"name": name, "context": context, "data_dict": data_dict})

    monkeypatch.setattr(validate_auth.toolkit, "check_access", fake_check_access)

    username = "alice"
    result = validate_auth.resource_validation_show({"user": username}, {"id": "res-2"})

    assert result == {"success": True}
    assert captured == {
        "name": "resource_show",
        "context": {"user": username},
        "data_dict": {"id": "res-2"},
    }


def test_resource_validation_show_auth_returns_false_when_unauthorized(monkeypatch):
    def fake_check_access(name, context, data_dict):
        raise toolkit.NotAuthorized()

    monkeypatch.setattr(validate_auth.toolkit, "check_access", fake_check_access)

    result = validate_auth.resource_validation_show({}, {"id": "res-2"})

    assert result == {
        "success": False,
        "msg": "Not authorized to view this resource",
    }
