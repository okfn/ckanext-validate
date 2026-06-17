import datetime
import pytest

from types import SimpleNamespace

from ckanext.validate import jobs
from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob
from ckanext.validate.tests.conftest import status_value
from ckanext.validate.blueprints import admin


def test_run_resource_validation_job_updates_only_the_target_job_record(monkeypatch):
    resource_id = "res-target-job-only"

    older_job = ValidationJob.create(resource_id=resource_id, status=JobStatus.ERROR)
    target_job = ValidationJob.create(resource_id=resource_id, status=JobStatus.QUEUED)

    older_job.create_timestamp = datetime.datetime(2026, 1, 1, 12, 0, 0)
    older_job.commit()

    target_job.create_timestamp = datetime.datetime(2026, 1, 1, 12, 1, 0)
    target_job.commit()

    def fake_get_site_user(context, data_dict):
        assert context == {"ignore_auth": True}
        assert data_dict == {}
        return {"name": "site-user"}

    def fake_resource_validate(context, data_dict):
        assert context == {"ignore_auth": True, "user": "site-user"}
        assert data_dict == {"id": resource_id}
        return {"id": resource_id}

    def fake_get_action(name):
        if name == "get_site_user":
            return fake_get_site_user
        if name == "resource_validate":
            return fake_resource_validate
        raise AssertionError(f"Unexpected action requested: {name}")

    monkeypatch.setattr(jobs.toolkit, "get_action", fake_get_action)

    jobs.run_resource_validation_job(resource_id, job_id=target_job.id)

    refreshed_older_job = ValidationJob.get(older_job.id)
    refreshed_target_job = ValidationJob.get(target_job.id)

    assert status_value(refreshed_older_job.status) == "error"
    assert refreshed_older_job.finish_timestamp is None

    assert status_value(refreshed_target_job.status) == "finished"
    assert refreshed_target_job.finish_timestamp is not None


def test_run_resource_validation_job_marks_only_target_job_as_error(monkeypatch):
    resource_id = "res-target-job-error-only"

    older_job = ValidationJob.create(resource_id=resource_id, status=JobStatus.FINISHED)
    target_job = ValidationJob.create(resource_id=resource_id, status=JobStatus.QUEUED)

    older_job.create_timestamp = datetime.datetime(2026, 1, 1, 13, 0, 0)
    older_job.finish_timestamp = datetime.datetime(2026, 1, 1, 13, 0, 5)
    older_job.commit()

    target_job.create_timestamp = datetime.datetime(2026, 1, 1, 13, 1, 0)
    target_job.commit()

    def fake_get_site_user(context, data_dict):
        return {"name": "site-user"}

    def fake_resource_validate(context, data_dict):
        raise RuntimeError("boom")

    def fake_get_action(name):
        if name == "get_site_user":
            return fake_get_site_user
        if name == "resource_validate":
            return fake_resource_validate
        raise AssertionError(f"Unexpected action requested: {name}")

    monkeypatch.setattr(jobs.toolkit, "get_action", fake_get_action)

    jobs.run_resource_validation_job(resource_id, job_id=target_job.id)

    refreshed_older_job = ValidationJob.get(older_job.id)
    refreshed_target_job = ValidationJob.get(target_job.id)

    assert status_value(refreshed_older_job.status) == "finished"
    assert refreshed_older_job.finish_timestamp is not None

    assert status_value(refreshed_target_job.status) == "error"
    assert refreshed_target_job.finish_timestamp is not None


def test_run_resource_validation_job_calls_resource_validate_with_site_user(monkeypatch):
    captured = {}
    state_calls = []

    def fake_get_site_user(context, data_dict):
        assert context == {"ignore_auth": True}
        assert data_dict == {}
        return {"name": "site-user"}

    def fake_resource_validate(context, data_dict):
        captured["context"] = context
        captured["data_dict"] = data_dict
        return {"id": "res-1"}

    def fake_get_action(name):
        if name == "get_site_user":
            return fake_get_site_user
        if name == "resource_validate":
            return fake_resource_validate
        raise AssertionError(f"Unexpected action requested: {name}")

    monkeypatch.setattr(jobs.toolkit, "get_action", fake_get_action)
    monkeypatch.setattr(
        jobs.ValidationJob,
        "create",
        lambda resource_id, status: SimpleNamespace(id=123),
    )
    monkeypatch.setattr(
        jobs.ValidationJob,
        "update_by_id",
        lambda job_id, status: state_calls.append(("update_by_id", job_id, status)),
    )

    jobs.run_resource_validation_job("res-1", job_id=123)

    assert captured == {
        "context": {"ignore_auth": True, "user": "site-user"},
        "data_dict": {"id": "res-1"},
    }
    assert state_calls == [
        ("update_by_id", 123, JobStatus.RUNNING),
        ("update_by_id", 123, JobStatus.FINISHED),
    ]


def test_run_resource_validation_job_marks_error_when_validation_fails(monkeypatch):
    state_calls = []

    def fake_get_site_user(context, data_dict):
        return {"name": "site-user"}

    def fake_resource_validate(context, data_dict):
        raise RuntimeError("boom")

    def fake_get_action(name):
        if name == "get_site_user":
            return fake_get_site_user
        if name == "resource_validate":
            return fake_resource_validate
        raise AssertionError(f"Unexpected action requested: {name}")

    monkeypatch.setattr(jobs.toolkit, "get_action", fake_get_action)
    monkeypatch.setattr(
        jobs.ValidationJob,
        "create",
        lambda resource_id, status: SimpleNamespace(id=456),
    )
    monkeypatch.setattr(
        jobs.ValidationJob,
        "update_by_id",
        lambda job_id, status: state_calls.append(("update_by_id", job_id, status)),
    )

    jobs.run_resource_validation_job("res-2", job_id=456)

    assert state_calls == [
        ("update_by_id", 456, JobStatus.RUNNING),
        ("update_by_id", 456, JobStatus.ERROR),
    ]


def test_run_resource_validation_job_returns_early_when_job_record_does_not_exist(monkeypatch):
    resource_validate_called = []
    state_calls = []

    def fake_get_site_user(context, data_dict):
        return {"name": "site-user"}

    def fake_resource_validate(context, data_dict):
        resource_validate_called.append(True)
        return {"id": "res-3"}

    def fake_get_action(name):
        if name == "get_site_user":
            return fake_get_site_user
        if name == "resource_validate":
            return fake_resource_validate
        raise AssertionError(f"Unexpected action requested: {name}")

    def fake_update_by_id(job_id, status):
        state_calls.append(("update_by_id", job_id, status))
        if status == JobStatus.RUNNING:
            raise ValueError("No existing job found for job_id")

    monkeypatch.setattr(jobs.toolkit, "get_action", fake_get_action)
    monkeypatch.setattr(jobs.ValidationJob, "update_by_id", fake_update_by_id)

    jobs.run_resource_validation_job("res-3", job_id=321)

    assert resource_validate_called == []
    assert state_calls == [
        ("update_by_id", 321, JobStatus.RUNNING),
    ]


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
def test_validation_jobs_uses_fresh_context_for_each_resource(app, monkeypatch):
    """Ensure each resource_show call gets a fresh context.

    CKAN actions may mutate the context during execution, so the admin view
    must not reuse the same context across consecutive resource_show calls.
    """
    job_1 = ValidationJob.create(
        resource_id="resource-1",
        status=JobStatus.FINISHED,
    )
    job_2 = ValidationJob.create(
        resource_id="resource-2",
        status=JobStatus.FINISHED,
    )

    monkeypatch.setattr(
        admin.toolkit,
        "current_user",
        SimpleNamespace(name="sysadmin", sysadmin=True),
    )
    monkeypatch.setattr(
        admin.ValidationJob,
        "get_all",
        lambda status=None, limit=100: [job_1, job_2],
    )
    monkeypatch.setattr(
        admin.toolkit,
        "url_for",
        lambda *args, **kwargs: f"/resource/{kwargs['resource_id']}",
    )

    contexts = []

    def fake_resource_show(context, data_dict):
        contexts.append(dict(context))

        # Simulate CKAN actions mutating the context during execution.
        context["dirty"] = True

        return {
            "id": data_dict["id"],
            "name": data_dict["id"],
            "package_id": "dataset-1",
        }

    def fake_get_action(action_name):
        assert action_name == "resource_show"
        return fake_resource_show

    monkeypatch.setattr(admin.toolkit, "get_action", fake_get_action)
    monkeypatch.setattr(
        admin.base,
        "render",
        lambda template, extra_vars: "ok",
    )

    response = app.get("/ckan-admin/validation-jobs")

    assert response.status_code == 200
    assert contexts == [
        {"user": "sysadmin"},
        {"user": "sysadmin"},
    ]
