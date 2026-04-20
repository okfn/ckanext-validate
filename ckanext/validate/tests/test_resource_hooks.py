from ckanext.validate import jobs
from ckanext.validate import resource_hooks


def test_build_validation_job_id_is_deterministic():
    assert resource_hooks.build_validation_job_id("res-1") == "validate-resource-res-1"


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
