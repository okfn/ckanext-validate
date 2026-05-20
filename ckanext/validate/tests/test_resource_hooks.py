from types import SimpleNamespace

from ckanext.validate import jobs
from ckanext.validate import resource_hooks
from ckanext.validate.model.validation_jobs import JobStatus


def test_enqueue_resource_validation_job_creates_db_job_and_enqueues_with_job_id_arg(monkeypatch):
    captured = {}

    def fake_create(resource_id, status):
        captured["created"] = (resource_id, status)
        return SimpleNamespace(id=1)

    def fake_enqueue_job(fn, args=None, kwargs=None, title=None, queue="default", rq_kwargs=None):
        captured["fn"] = fn
        captured["args"] = args
        captured["kwargs"] = kwargs
        captured["title"] = title
        captured["queue"] = queue
        captured["rq_kwargs"] = rq_kwargs
        return "queued-job"

    monkeypatch.setattr(
        resource_hooks.ValidationJob,
        "get_latest_job_status_for_resource",
        lambda resource_id: None,
    )
    monkeypatch.setattr(resource_hooks.ValidationJob, "create", fake_create)
    monkeypatch.setattr(resource_hooks.toolkit, "enqueue_job", fake_enqueue_job)

    result = resource_hooks.enqueue_resource_validation_job("res-1")

    assert result == "queued-job"
    assert captured == {
        "created": ("res-1", JobStatus.QUEUED),
        "fn": jobs.run_resource_validation_job,
        "args": ["res-1", 1],
        "kwargs": None,
        "title": "Validate resource res-1",
        "queue": "default",
        "rq_kwargs": None,
    }


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

    assert result is None
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

    monkeypatch.setattr(
        resource_hooks,
        "enqueue_resource_validation_job",
        fake_enqueue_resource_validation_job,
    )

    result = resource_hooks.handle_resource_change(resource)

    assert result is None
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

    monkeypatch.setattr(
        resource_hooks,
        "enqueue_resource_validation_job",
        fake_enqueue_resource_validation_job,
    )

    result = resource_hooks.handle_resource_change(resource)

    assert result is None
    assert called == {"enqueue": False}


def test_enqueue_resource_validation_job_returns_none_when_enqueue_fails(monkeypatch):
    def fake_enqueue_job(fn, args=None, kwargs=None, title=None, queue="default", rq_kwargs=None):
        raise RuntimeError("already queued")

    monkeypatch.setattr(
        resource_hooks.ValidationJob,
        "get_latest_job_status_for_resource",
        lambda resource_id: None,
    )
    monkeypatch.setattr(
        resource_hooks.ValidationJob,
        "create",
        lambda resource_id, status: SimpleNamespace(id=1),
    )

    updated = {}

    def fake_update_by_id(job_id, status):
        updated["job_id"] = job_id
        updated["status"] = status

    monkeypatch.setattr(resource_hooks.ValidationJob, "update_by_id", fake_update_by_id)
    monkeypatch.setattr(resource_hooks.toolkit, "enqueue_job", fake_enqueue_job)

    assert resource_hooks.enqueue_resource_validation_job("res-1") is None
    assert updated == {"job_id": 1, "status": JobStatus.ERROR}
