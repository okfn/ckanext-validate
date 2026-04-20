import io
from pathlib import Path

import pytest
from ckan.plugins import toolkit

from ckanext.validate import jobs
from ckanext.validate import resource_hooks


def test_build_validation_job_id_is_deterministic():
    assert resource_hooks.build_validation_job_id("res-1") == "validate-resource-res-1"

FIXTURES_DIR = Path(__file__).parent / "files_test"


class FakeUpload:
    """Minimal file-like upload object for testing strict validation."""

    def __init__(self, content):
        if isinstance(content, str):
            content = content.encode("utf-8")
        self._buffer = io.BytesIO(content)

    def read(self):
        return self._buffer.read()

    def seek(self, pos):
        self._buffer.seek(pos)


def test_enqueue_resource_validation_job_uses_deterministic_job_id(monkeypatch):
    captured = {}

    def fake_enqueue_job(fn, args=None, kwargs=None, title=None, queue="default", rq_kwargs=None):
        captured["fn"] = fn
        captured["args"] = args
        captured["kwargs"] = kwargs
        captured["title"] = title
        captured["queue"] = queue
        captured["rq_kwargs"] = rq_kwargs
        return "job-123"

    monkeypatch.setattr(resource_hooks.toolkit, "enqueue_job", fake_enqueue_job)

    result = resource_hooks.enqueue_resource_validation_job("res-1")

    assert result == "job-123"
    assert captured == {
        "fn": jobs.run_resource_validation_job,
        "args": ["res-1"],
        "kwargs": None,
        "title": "Validate resource res-1",
        "queue": "default",
        "rq_kwargs": {"job_id": "validate-resource-res-1"},
    }


def test_enqueue_resource_validation_job_returns_none_when_enqueue_fails(monkeypatch):
    def fake_enqueue_job(fn, args=None, kwargs=None, title=None, queue="default", rq_kwargs=None):
        raise RuntimeError("already queued")

    monkeypatch.setattr(resource_hooks.toolkit, "enqueue_job", fake_enqueue_job)

    assert resource_hooks.enqueue_resource_validation_job("res-1") is None


def test_handle_resource_change_enqueues_job_for_eligible_resource(monkeypatch):
    resource = {
        "id": "res-2",
        "format": "CSV",
        "url_type": "upload",
        "url": "",
        "state": "active",
    }

    captured = {}

    def fake_enqueue_resource_validation_job(resource_id):
        captured["resource_id"] = resource_id
        return "job-123"

    monkeypatch.setattr(
        resource_hooks,
        "enqueue_resource_validation_job",
        fake_enqueue_resource_validation_job,
    )

    result = resource_hooks.handle_resource_change(resource)

    assert result is True
    assert captured == {"resource_id": "res-2"}


def test_handle_resource_change_skips_non_csv(monkeypatch):
    resource = {
        "id": "res-4",
        "format": "PDF",
        "url_type": "",
        "url": "http://example.com/file.pdf",
        "state": "active",
    }

    called = {"enqueue": False}

    def fake_enqueue_resource_validation_job(resource_id):
        called["enqueue"] = True

    monkeypatch.setattr(resource_hooks, "enqueue_resource_validation_job", fake_enqueue_resource_validation_job)

    result = resource_hooks.handle_resource_change(resource)

    assert result is False
    assert called == {"enqueue": False}


def test_handle_resource_change_skips_deleted_resource(monkeypatch):
    resource = {
        "id": "res-5",
        "format": "CSV",
        "url_type": "upload",
        "url": "",
        "state": "deleted",
    }

    called = {"enqueue": False}

    def fake_enqueue_resource_validation_job(resource_id):
        called["enqueue"] = True

    monkeypatch.setattr(resource_hooks, "enqueue_resource_validation_job", fake_enqueue_resource_validation_job)

    result = resource_hooks.handle_resource_change(resource)

    assert result is False
    assert called == {"enqueue": False}


# ---------------------------------------------------------------------------
# is_fail_on_invalid_upload_enabled
# ---------------------------------------------------------------------------


@pytest.mark.ckan_config("ckanext.validate.fail_on_invalid_upload", "false")
def test_is_fail_on_invalid_upload_enabled_returns_false_by_default():
    assert resource_hooks.is_fail_on_invalid_upload_enabled() is False


@pytest.mark.ckan_config("ckanext.validate.fail_on_invalid_upload", "true")
def test_is_fail_on_invalid_upload_enabled_returns_true_when_configured():
    assert resource_hooks.is_fail_on_invalid_upload_enabled() is True


@pytest.mark.ckan_config("ckanext.validate.fail_on_invalid_upload", "false")
def test_is_fail_on_invalid_upload_enabled_returns_false_when_configured():
    assert resource_hooks.is_fail_on_invalid_upload_enabled() is False


# ---------------------------------------------------------------------------
# validate_csv_upload_strict — skip conditions (strict mode disabled)
# ---------------------------------------------------------------------------


def test_validate_csv_upload_strict_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: False)
    data_dict = {"format": "CSV", "upload": FakeUpload("id,name\n1,Alice\n")}
    # Must not raise
    resource_hooks.validate_csv_upload_strict(data_dict)


def test_validate_csv_upload_strict_skips_non_csv(monkeypatch):
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: True)
    data_dict = {"format": "XLSX", "upload": FakeUpload("some data")}
    resource_hooks.validate_csv_upload_strict(data_dict)


def test_validate_csv_upload_strict_skips_when_no_upload_key(monkeypatch):
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: True)
    data_dict = {"format": "CSV"}
    resource_hooks.validate_csv_upload_strict(data_dict)


def test_validate_csv_upload_strict_skips_url_string_upload(monkeypatch):
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: True)
    data_dict = {"format": "CSV", "upload": "https://example.com/data.csv"}
    resource_hooks.validate_csv_upload_strict(data_dict)


def test_validate_csv_upload_strict_skips_empty_content(monkeypatch):
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: True)
    data_dict = {"format": "CSV", "upload": FakeUpload(b"")}
    resource_hooks.validate_csv_upload_strict(data_dict)


# ---------------------------------------------------------------------------
# validate_csv_upload_strict — strict mode enabled, valid CSV
# ---------------------------------------------------------------------------


def test_validate_csv_upload_strict_valid_csv_does_not_raise(monkeypatch):
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: True)
    content = (FIXTURES_DIR / "valid.csv").read_bytes()
    data_dict = {"format": "CSV", "upload": FakeUpload(content)}
    resource_hooks.validate_csv_upload_strict(data_dict)


def test_validate_csv_upload_strict_resets_upload_position_after_valid(monkeypatch):
    """Upload must be seeked back to 0 so CKAN can still read it for the actual save."""
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: True)
    content = (FIXTURES_DIR / "valid.csv").read_bytes()
    upload = FakeUpload(content)
    data_dict = {"format": "CSV", "upload": upload}
    resource_hooks.validate_csv_upload_strict(data_dict)
    assert upload.read() == content


# ---------------------------------------------------------------------------
# validate_csv_upload_strict — strict mode enabled, invalid CSV
# ---------------------------------------------------------------------------


def test_validate_csv_upload_strict_invalid_csv_raises_validation_error(monkeypatch):
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: True)
    content = (FIXTURES_DIR / "bike-errors.csv").read_bytes()
    data_dict = {"format": "CSV", "upload": FakeUpload(content)}
    with pytest.raises(toolkit.ValidationError) as exc:
        resource_hooks.validate_csv_upload_strict(data_dict)
    assert "upload" in exc.value.error_dict
    assert exc.value.error_dict["upload"]


def test_validate_csv_upload_strict_error_messages_are_strings(monkeypatch):
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: True)
    content = (FIXTURES_DIR / "bike-errors.csv").read_bytes()
    data_dict = {"format": "CSV", "upload": FakeUpload(content)}
    with pytest.raises(toolkit.ValidationError) as exc:
        resource_hooks.validate_csv_upload_strict(data_dict)
    for msg in exc.value.error_dict["upload"]:
        assert isinstance(msg, str)


def test_validate_csv_upload_strict_frictionless_exception_raises_validation_error(monkeypatch):
    monkeypatch.setattr(resource_hooks, "is_fail_on_invalid_upload_enabled", lambda: True)

    def explode(source, format):
        raise RuntimeError("frictionless crashed")

    monkeypatch.setattr(resource_hooks, "FrictionlessResource", explode)
    data_dict = {"format": "CSV", "upload": FakeUpload("id,name\n1,Alice\n")}
    with pytest.raises(toolkit.ValidationError) as exc:
        resource_hooks.validate_csv_upload_strict(data_dict)
    assert "upload" in exc.value.error_dict
