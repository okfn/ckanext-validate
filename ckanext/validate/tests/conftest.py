import pytest
from ckanext.validate.actions import action as validate_action


class DummyUploader:
    def __init__(self, path):
        self.path = str(path)

    def get_path(self, resource_id):
        return self.path


class DummyReport:
    def __init__(self, valid, tasks=None):
        self.valid = valid
        self.tasks = tasks or []

    def to_descriptor(self):
        return {"valid": self.valid}


class DummyResource:
    def __init__(self, source, format):
        self.source = source
        self.format = format

    def validate(self):
        return DummyReport(valid=True)


@pytest.fixture
def fake_actions(monkeypatch):
    calls = {"resource_patch": []}

    def _factory(resource):
        def fake_check_access(name, context, data_dict):
            calls["check_access"] = {
                "name": name,
                "context": context,
                "data_dict": data_dict,
            }

        def fake_resource_show(context, data_dict):
            calls["resource_show"] = {
                "context": context,
                "data_dict": data_dict,
            }
            return resource

        def fake_resource_patch(context, data_dict):
            calls["resource_patch"].append(
                {"context": context, "data_dict": data_dict}
            )
            updated = dict(resource)
            updated.update(data_dict)
            return updated

        def fake_get_action(name):
            if name == "resource_show":
                return fake_resource_show
            if name == "resource_patch":
                return fake_resource_patch
            raise AssertionError(f"Unexpected action requested: {name}")

        monkeypatch.setattr(validate_action.toolkit, "check_access", fake_check_access)
        monkeypatch.setattr(validate_action.toolkit, "get_action", fake_get_action)
        return calls

    return _factory


@pytest.fixture
def clean_db(reset_db, migrate_db_for):
    """Clean and initialize the database."""
    reset_db()
    migrate_db_for("validate")
