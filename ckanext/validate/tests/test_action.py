
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from ckan.plugins import toolkit
from ckanext.validate.actions import action as validate_action
from .conftest import DummyUploader, DummyReport, DummyResource

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_resource_validate_rejects_non_csv(monkeypatch, fake_actions):
    resource = {
        "id": "res-non-csv",
        "format": "XLSX",
        "url": "http://example.com/file.xlsx",
        "url_type": "",
    }
    fake_actions(resource)

    with pytest.raises(toolkit.ValidationError) as exc:
        validate_action.resource_validate({}, {"id": resource["id"]})

    assert exc.value.error_dict == {
        "format": ["Only CSV resources can be validated."]
    }


def test_resource_validate_uploaded_file_success(monkeypatch, fake_actions):
    resource = {
        "id": "res-upload-ok",
        "format": "CSV",
        "url_type": "upload",
        "url": "",
    }
    calls = fake_actions(resource)
    created = {}

    def fake_create(resource_id, status, error_count, errors):
        created.update(
            {
                "resource_id": resource_id,
                "status": status,
                "error_count": error_count,
                "errors": errors,
            }
        )

    monkeypatch.setattr(validate_action.uploader, "get_resource_uploader", lambda r: DummyUploader(FIXTURES_DIR / "valid.csv"))
    monkeypatch.setattr(validate_action.system, "use_context", lambda trusted=True: nullcontext())
    monkeypatch.setattr(validate_action, "Resource", DummyResource)
    monkeypatch.setattr(validate_action.Validation, "create", fake_create)

    result = validate_action.resource_validate({}, {"id": resource["id"]})

    assert calls["check_access"]["name"] == "resource_update"
    assert created == {
        "resource_id": "res-upload-ok",
        "status": "success",
        "error_count": 0,
        "errors": [],
    }
    assert result["validation_status"] == "success"
    assert result["validation_error_count"] == 0
    assert result["validation_errors"] == "[]"

    patch_call = calls["resource_patch"][0]
    assert patch_call["context"] == {"ignore_auth": True}
    assert patch_call["data_dict"]["id"] == "res-upload-ok"


def test_resource_validate_collects_task_errors(monkeypatch, fake_actions):
    resource = {
        "id": "res-invalid",
        "format": "CSV",
        "url_type": "",
        "url": "https://example.com/bad.csv",
    }
    fake_actions(resource)
    created = {}

    error_1 = SimpleNamespace(row_number=3, field_name="price", message="type error")
    error_2 = SimpleNamespace(row_number=6, field_name="stock", message="constraint error")
    report = DummyReport(valid=False, tasks=[SimpleNamespace(errors=[error_1]), SimpleNamespace(errors=[error_2])])

    class InvalidResource(DummyResource):
        def validate(self):
            return report

    monkeypatch.setattr(validate_action, "Resource", InvalidResource)
    monkeypatch.setattr(validate_action.Validation, "create", lambda resource_id, status, error_count, errors: created.update({
        "resource_id": resource_id,
        "status": status,
        "error_count": error_count,
        "errors": errors,
    }))

    result = validate_action.resource_validate({}, {"id": resource["id"]})

    assert result["validation_status"] == "failure"
    assert result["validation_error_count"] == 2
    assert created["status"] == "failure"
    assert created["error_count"] == 2
    assert created["errors"] == [
        {"row": 3, "field": "price", "message": "type error"},
        {"row": 6, "field": "stock", "message": "constraint error"},
    ]


def test_resource_validate_adds_structural_error_when_report_has_no_task_errors(
    monkeypatch, fake_actions
):
    resource = {
        "id": "res-structural",
        "format": "CSV",
        "url_type": "",
        "url": "https://example.com/structural.csv",
    }
    fake_actions(resource)
    created = {}

    class StructuralResource(DummyResource):
        def validate(self):
            return DummyReport(valid=False, tasks=[])

    monkeypatch.setattr(validate_action, "Resource", StructuralResource)
    monkeypatch.setattr(validate_action.Validation, "create", lambda resource_id, status, error_count, errors: created.update({
        "resource_id": resource_id,
        "status": status,
        "error_count": error_count,
        "errors": errors,
    }))

    result = validate_action.resource_validate({}, {"id": resource["id"]})

    assert result["validation_status"] == "failure"
    assert result["validation_error_count"] == 1
    assert created["errors"] == [
        {
            "message": "Structural validation error",
            "code": "structure-error",
        }
    ]


def test_resource_validate_wraps_frictionless_exceptions(monkeypatch, fake_actions):
    resource = {
        "id": "res-exception",
        "format": "CSV",
        "url_type": "",
        "url": "https://example.com/boom.csv",
    }
    fake_actions(resource)

    class BrokenResource(DummyResource):
        def validate(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(validate_action, "Resource", BrokenResource)

    with pytest.raises(toolkit.ValidationError) as exc:
        validate_action.resource_validate({}, {"id": resource["id"]})

    assert exc.value.error_dict == {"frictionless": ["System error: boom"]}


def test_resource_validation_show_returns_latest_record(monkeypatch):
    expected = {
        "id": 7,
        "resource_id": "res-show",
        "status": "failure",
        "error_count": 1,
        "errors": [{"message": "bad row"}],
        "created": "2026-03-25T10:00:00",
    }

    monkeypatch.setattr(validate_action.toolkit, "check_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        validate_action.Validation,
        "get_latest",
        lambda resource_id: SimpleNamespace(as_dict=lambda: expected),
    )

    result = validate_action.resource_validation_show({}, {"id": "res-show"})

    assert result == expected


def test_resource_validation_show_raises_not_found_when_missing(monkeypatch):
    monkeypatch.setattr(validate_action.toolkit, "check_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(validate_action.Validation, "get_latest", lambda resource_id: None)

    with pytest.raises(toolkit.ObjectNotFound, match="No validation found for resource res-missing"):
        validate_action.resource_validation_show({}, {"id": "res-missing"})


def test_resource_validate_with_real_frictionless_fixture_file(monkeypatch, fake_actions):
    resource = {
        "id": "res-real-invalid",
        "format": "CSV",
        "url_type": "",
        "url": (FIXTURES_DIR / "so-wrong.csv").resolve().as_uri(),
    }
    fake_actions(resource)
    created = {}

    monkeypatch.setattr(
        validate_action.Validation,
        "create",
        lambda resource_id, status, error_count, errors: created.update(
            {
                "resource_id": resource_id,
                "status": status,
                "error_count": error_count,
                "errors": errors,
            }
        ),
    )

    result = validate_action.resource_validate({}, {"id": resource["id"]})

    assert result["validation_status"] == "failure"
    assert result["validation_error_count"] >= 1
    assert created["status"] == "failure"
    assert created["error_count"] >= 1
