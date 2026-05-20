import pytest
from ckanext.validate.model import ValidationJob
from ckan.tests import factories


def status_value(value):
    return value.value if hasattr(value, "value") else value


class DummyUploader:
    def __init__(self, path):
        self.path = str(path)

    def get_path(self, resource_id):
        return self.path

    def upload(self, id, max_size):
        pass


class DummyReport:
    def __init__(self, valid, tasks=None):
        self.valid = valid
        self.tasks = tasks or []

    def to_descriptor(self):
        tasks = []
        for task in self.tasks:
            errors = []
            for e in (task.errors if hasattr(task, "errors") else []):
                if isinstance(e, dict):
                    errors.append(e)
                else:
                    errors.append({
                        "rowNumber": getattr(e, "row_number", None),
                        "fieldName": getattr(e, "field_name", None),
                        "message": getattr(e, "message", ""),
                    })
            tasks.append({"errors": errors})
        return {"valid": self.valid, "tasks": tasks}


class DummyResource:
    def __init__(self, source, format):
        self.source = source
        self.format = format

    def validate(self):
        return DummyReport(valid=True)


@pytest.fixture(autouse=True)
def validate_setup(with_plugins, reset_db, migrate_db_for):
    reset_db()
    migrate_db_for("validate")


@pytest.fixture
def make_validation_job():
    def _make(resource_id=None, status="finished"):
        if resource_id is None:
            resource = factories.Resource(format="CSV")
            resource_id = resource["id"]

        return ValidationJob.create(
            resource_id=resource_id,
            status=status,
        )

    return _make
