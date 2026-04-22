from ckanext.validate import jobs
from ckanext.validate.model.validation_jobs import JobStatus


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
        lambda resource_id, status: state_calls.append(("create", resource_id, status)),
    )
    monkeypatch.setattr(
        jobs.ValidationJob,
        "update",
        lambda resource_id, status: state_calls.append(("update", resource_id, status)),
    )

    jobs.run_resource_validation_job("res-1")

    assert captured == {
        "context": {"ignore_auth": True, "user": "site-user"},
        "data_dict": {"id": "res-1"},
    }
    assert state_calls == [
        ("update", "res-1", JobStatus.RUNNING),
        ("update", "res-1", JobStatus.FINISHED),
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
        lambda resource_id, status: state_calls.append(("create", resource_id, status)),
    )
    monkeypatch.setattr(
        jobs.ValidationJob,
        "update",
        lambda resource_id, status: state_calls.append(("update", resource_id, status)),
    )

    jobs.run_resource_validation_job("res-2")

    assert state_calls == [
        ("update", "res-2", JobStatus.RUNNING),
        ("update", "res-2", JobStatus.ERROR),
    ]


def test_run_resource_validation_job_creates_running_when_job_record_does_not_exist(monkeypatch):
    captured = {}
    state_calls = []

    def fake_get_site_user(context, data_dict):
        return {"name": "site-user"}

    def fake_resource_validate(context, data_dict):
        captured["context"] = context
        captured["data_dict"] = data_dict
        return {"id": "res-3"}

    def fake_get_action(name):
        if name == "get_site_user":
            return fake_get_site_user
        if name == "resource_validate":
            return fake_resource_validate
        raise AssertionError(f"Unexpected action requested: {name}")

    def fake_update(resource_id, status):
        state_calls.append(("update", resource_id, status))
        if status == JobStatus.RUNNING:
            raise ValueError("No existing job found")

    monkeypatch.setattr(jobs.toolkit, "get_action", fake_get_action)
    monkeypatch.setattr(
        jobs.ValidationJob,
        "create",
        lambda resource_id, status: state_calls.append(("create", resource_id, status)),
    )
    monkeypatch.setattr(jobs.ValidationJob, "update", fake_update)

    jobs.run_resource_validation_job("res-3")

    assert captured == {
        "context": {"ignore_auth": True, "user": "site-user"},
        "data_dict": {"id": "res-3"},
    }
    assert state_calls == [
        ("update", "res-3", JobStatus.RUNNING),
        ("create", "res-3", JobStatus.RUNNING),
        ("update", "res-3", JobStatus.FINISHED),
    ]
