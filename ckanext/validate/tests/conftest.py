import pytest


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
def clean_db(reset_db, migrate_db_for):
    reset_db()
    migrate_db_for("validate")
