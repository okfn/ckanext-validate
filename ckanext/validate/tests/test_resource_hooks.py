from types import SimpleNamespace

import pytest
from ckan.tests import factories, helpers

from ckanext.validate import jobs
from ckanext.validate import resource_hooks
from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob
from ckanext.validate.tests.conftest import status_value


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


@pytest.mark.parametrize("pending_status", list(JobStatus.pending_statuses()))
def test_enqueue_resource_validation_job_skips_when_latest_job_is_pending(
    monkeypatch, pending_status
):
    calls = {"create": False, "enqueue": False}

    monkeypatch.setattr(
        resource_hooks.ValidationJob,
        "get_latest_job_status_for_resource",
        lambda resource_id: pending_status,
    )

    def fake_create(*args, **kwargs):
        calls["create"] = True

    def fake_enqueue_job(*args, **kwargs):
        calls["enqueue"] = True

    monkeypatch.setattr(resource_hooks.ValidationJob, "create", fake_create)
    monkeypatch.setattr(resource_hooks.toolkit, "enqueue_job", fake_enqueue_job)

    result = resource_hooks.enqueue_resource_validation_job("res-pending")

    assert result is None
    assert calls == {"create": False, "enqueue": False}


def test_enqueue_resource_validation_job_marks_created_job_as_error_in_db_when_enqueue_fails(
    monkeypatch,
):
    created_job = ValidationJob.create(resource_id="res-enqueue-db-error", status="queued")

    monkeypatch.setattr(
        resource_hooks.ValidationJob,
        "get_latest_job_status_for_resource",
        lambda resource_id: None,
    )
    monkeypatch.setattr(
        resource_hooks.ValidationJob,
        "create",
        lambda resource_id, status: SimpleNamespace(id=created_job.id),
    )

    def fake_enqueue_job(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(resource_hooks.toolkit, "enqueue_job", fake_enqueue_job)

    result = resource_hooks.enqueue_resource_validation_job("res-enqueue-db-error")

    refreshed = ValidationJob.get(created_job.id)

    assert result is None
    assert status_value(refreshed.status) == "error"
    assert refreshed.finish_timestamp is not None


@pytest.mark.parametrize("resource", [None, {}])
def test_cleanup_resource_jobs_skips_when_resource_has_no_id(monkeypatch, resource):
    called = {"delete": False}

    def fake_delete_for_resource(resource_id):
        called["delete"] = True

    monkeypatch.setattr(
        resource_hooks.ValidationJob,
        "delete_for_resource",
        fake_delete_for_resource,
    )

    result = resource_hooks.cleanup_resource_jobs(resource)

    assert result is None
    assert called == {"delete": False}


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
def test_resource_delete_action_removes_validation_jobs_for_deleted_resource(monkeypatch):
    # Avoid auto-enqueueing validation jobs while creating resources in the test.
    monkeypatch.setattr(
        resource_hooks,
        "handle_resource_change",
        lambda *args, **kwargs: None,
    )

    sysadmin = factories.Sysadmin()
    dataset = factories.Dataset()

    resource = factories.Resource(
        package_id=dataset["id"],
        format="CSV",
    )
    other_resource = factories.Resource(
        package_id=dataset["id"],
        format="CSV",
    )

    job_a = ValidationJob.create(
        resource_id=resource["id"],
        status=JobStatus.QUEUED,
    )
    job_b = ValidationJob.create(
        resource_id=resource["id"],
        status=JobStatus.FINISHED,
    )
    other_job = ValidationJob.create(
        resource_id=other_resource["id"],
        status=JobStatus.QUEUED,
    )

    helpers.call_action(
        "resource_delete",
        context={"user": sysadmin["name"]},
        id=resource["id"],
    )

    assert ValidationJob.get(job_a.id) is None
    assert ValidationJob.get(job_b.id) is None
    assert ValidationJob.get_latest_job_for_resource(resource["id"]) is None

    # Sanity check: deleting one resource must not remove jobs from another resource.
    assert ValidationJob.get(other_job.id) is not None
