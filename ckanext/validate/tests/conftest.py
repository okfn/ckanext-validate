import pytest


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
        return {"valid": self.valid}


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
