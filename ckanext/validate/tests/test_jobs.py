import json

import pytest

from ckanext.validate import jobs

_INTERNAL_PATCH_FLAG = "_validate_internal_patch"


def test_run_resource_validation_job_calls_resource_validate_with_user(monkeypatch):
    captured = {}

    def fake_resource_validate(context, data_dict):
        captured["context"] = context
        captured["data_dict"] = data_dict
        return {"id": "res-1", "validation_status": "success"}

    def fake_get_action(name):
        assert name == "resource_validate"
        return fake_resource_validate

    monkeypatch.setattr(jobs.toolkit, "get_action", fake_get_action)

    jobs.run_resource_validation_job("res-1", "alice")

    assert captured == {
        "context": {"ignore_auth": True, "user": "alice"},
        "data_dict": {"id": "res-1"},
    }


def test_run_resource_validation_job_patches_error_with_user_and_internal_flag(monkeypatch):
    captured = {}

    def fake_resource_validate(context, data_dict):
        raise RuntimeError("boom")

    def fake_resource_patch(context, data_dict):
        captured["context"] = context
        captured["data_dict"] = data_dict
        return data_dict

    def fake_get_action(name):
        if name == "resource_validate":
            return fake_resource_validate
        if name == "resource_patch":
            return fake_resource_patch
        raise AssertionError(f"Unexpected action requested: {name}")

    monkeypatch.setattr(jobs.toolkit, "get_action", fake_get_action)

    with pytest.raises(RuntimeError, match="boom"):
        jobs.run_resource_validation_job("res-2", "alice")

    assert captured["context"] == {
        "ignore_auth": True,
        _INTERNAL_PATCH_FLAG: True,
        "user": "alice",
    }
    assert captured["data_dict"]["id"] == "res-2"
    assert captured["data_dict"]["validation_status"] == "error"
    assert captured["data_dict"]["validation_error_count"] is None

    errors = json.loads(captured["data_dict"]["validation_errors"])
    assert errors == [{"message": "System error: boom"}]
