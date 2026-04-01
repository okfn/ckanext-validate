from ckanext.validate import jobs
from ckanext.validate import resource_hooks

_INTERNAL_PATCH_FLAG = "_validate_internal_patch"


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
