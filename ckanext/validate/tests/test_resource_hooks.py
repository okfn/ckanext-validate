import io
from pathlib import Path

import pytest
from ckan.plugins import toolkit

from ckanext.validate import jobs
from ckanext.validate import resource_hooks

_INTERNAL_PATCH_FLAG = "_validate_internal_patch"

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


def test_mark_resource_as_pending_uses_internal_flag_and_user(monkeypatch):
    captured = {}

    def fake_resource_patch(context, data_dict):
        captured["context"] = context
        captured["data_dict"] = data_dict
        return data_dict

    def fake_get_action(name):
        assert name == "resource_patch"
        return fake_resource_patch

    monkeypatch.setattr(resource_hooks.toolkit, "get_action", fake_get_action)

    username = "alice"
    resource_hooks.mark_resource_as_pending("res-1", username)

    assert captured["context"] == {
        "ignore_auth": True,
        _INTERNAL_PATCH_FLAG: True,
        "user": username,
    }
    assert captured["data_dict"] == {
        "id": "res-1",
        "validation_status": "pending",
        "validation_error_count": None,
        "validation_errors": None,
    }


def test_enqueue_resource_validation_job_passes_username(monkeypatch):
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

    username = "alice"
    result = resource_hooks.enqueue_resource_validation_job("res-1", username)

    assert result == "job-123"
    assert captured == {
        "fn": jobs.run_resource_validation_job,
        "args": ["res-1", username],
        "kwargs": None,
        "title": "Validate resource res-1",
        "queue": "validate",
        "rq_kwargs": None,
    }


def test_handle_resource_change_marks_pending_and_enqueues_job(monkeypatch):
    resource = {
        "id": "res-2",
        "format": "CSV",
        "url_type": "upload",
        "url": "",
        "state": "active",
    }

    calls = {
        "pending": [],
        "enqueue": [],
    }

    def fake_mark_resource_as_pending(resource_id, username=None):
        calls["pending"].append((resource_id, username))

    def fake_enqueue_resource_validation_job(resource_id, username=None):
        calls["enqueue"].append((resource_id, username))
        return "job-123"

    monkeypatch.setattr(
        resource_hooks,
        "mark_resource_as_pending",
        fake_mark_resource_as_pending,
    )
    monkeypatch.setattr(
        resource_hooks,
        "enqueue_resource_validation_job",
        fake_enqueue_resource_validation_job,
    )

    username = "alice"
    result = resource_hooks.handle_resource_change({"user": username}, resource, "create")

    assert result is True
    assert calls["pending"] == [("res-2", username)]
    assert calls["enqueue"] == [("res-2", username)]


def test_handle_resource_change_skips_internal_patch_reentry(monkeypatch):
    resource = {
        "id": "res-3",
        "format": "CSV",
        "url_type": "upload",
        "url": "",
        "state": "active",
    }

    called = {"pending": False, "enqueue": False}

    def fake_mark_resource_as_pending(resource_id, username=None):
        called["pending"] = True

    def fake_enqueue_resource_validation_job(resource_id, username=None):
        called["enqueue"] = True

    monkeypatch.setattr(resource_hooks, "mark_resource_as_pending", fake_mark_resource_as_pending)
    monkeypatch.setattr(resource_hooks, "enqueue_resource_validation_job", fake_enqueue_resource_validation_job)

    username = "alice"
    result = resource_hooks.handle_resource_change(
        {_INTERNAL_PATCH_FLAG: True, "user": username},
        resource,
        "update",
    )

    assert result is False
    assert called == {"pending": False, "enqueue": False}


def test_handle_resource_change_skips_non_csv(monkeypatch):
    resource = {
        "id": "res-4",
        "format": "PDF",
        "url_type": "",
        "url": "http://example.com/file.pdf",
        "state": "active",
    }

    called = {"pending": False, "enqueue": False}

    def fake_mark_resource_as_pending(resource_id, username=None):
        called["pending"] = True

    def fake_enqueue_resource_validation_job(resource_id, username=None):
        called["enqueue"] = True

    monkeypatch.setattr(resource_hooks, "mark_resource_as_pending", fake_mark_resource_as_pending)
    monkeypatch.setattr(resource_hooks, "enqueue_resource_validation_job", fake_enqueue_resource_validation_job)

    username = "alice"
    result = resource_hooks.handle_resource_change({"user": username}, resource, "update")

    assert result is False
    assert called == {"pending": False, "enqueue": False}


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
