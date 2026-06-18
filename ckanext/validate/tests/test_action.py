import pytest

from pathlib import Path
from types import SimpleNamespace

from ckan.plugins import toolkit
from ckan.tests import factories, helpers

from ckanext.validate.actions import action as validate_action
from ckanext.validate.model.validation import Validation
from .conftest import DummyUploader, DummyReport, DummyResource

FIXTURES_DIR = Path(__file__).parent / "files_test"


@pytest.fixture(autouse=True)
def disable_auto_validation(monkeypatch):
    """Prevent auto-validation hooks from firing when factories create CSV resources."""
    from ckanext.validate import resource_hooks
    monkeypatch.setattr(resource_hooks, "handle_resource_change", lambda *a, **kw: False)


def test_resource_validate_rejects_non_csv():
    resource = factories.Resource(format="XLSX", url="http://example.com/file.xlsx")
    sysadmin = factories.Sysadmin()

    with pytest.raises(toolkit.ValidationError) as exc:
        validate_action.resource_validate(
            {"user": sysadmin["name"]}, {"id": resource["id"]}
        )

    assert exc.value.error_dict == {
        "format": ["Only CSV resources can be validated."]
    }


def test_resource_validate_raises_not_authorized(monkeypatch):
    def fake_check_access(name, context, data_dict):
        raise toolkit.NotAuthorized()

    monkeypatch.setattr(validate_action.toolkit, "check_access", fake_check_access)

    with pytest.raises(toolkit.NotAuthorized):
        validate_action.resource_validate({"user": "alice"}, {"id": "res-unauthorized"})


def test_resource_validate_uploaded_file_success(monkeypatch):
    resource = factories.Resource(format="CSV", url_type="upload", url="")
    sysadmin = factories.Sysadmin()

    monkeypatch.setattr(
        validate_action.uploader,
        "get_resource_uploader",
        lambda r: DummyUploader(FIXTURES_DIR / "valid.csv"),
    )

    result = validate_action.resource_validate(
        {"user": sysadmin["name"]}, {"id": resource["id"]}
    )

    assert result["id"] == resource["id"]

    record = Validation.get_latest(resource["id"])
    assert record is not None
    assert record.status == "success"
    assert record.error_count == 0
    assert record.errors == []


def test_resource_validate_collects_task_errors(monkeypatch):
    resource = factories.Resource(
        format="CSV", url_type="", url="https://example.com/bad.csv"
    )
    sysadmin = factories.Sysadmin()

    error_1 = SimpleNamespace(row_number=3, field_name="price", message="type error")
    error_2 = SimpleNamespace(row_number=6, field_name="stock", message="constraint error")
    report = DummyReport(
        valid=False,
        tasks=[
            SimpleNamespace(errors=[error_1]),
            SimpleNamespace(errors=[error_2]),
        ],
    )

    class InvalidResource(DummyResource):
        def validate(self):
            return report

    monkeypatch.setattr(validate_action, "Resource", InvalidResource)

    result = validate_action.resource_validate(
        {"user": sysadmin["name"]}, {"id": resource["id"]}
    )

    assert result["id"] == resource["id"]

    record = Validation.get_latest(resource["id"])
    assert record is not None
    assert record.status == "failure"
    assert record.error_count == 2
    assert record.errors == [
        {"rowNumber": 3, "fieldName": "price", "message": "type error"},
        {"rowNumber": 6, "fieldName": "stock", "message": "constraint error"},
    ]


def test_resource_validate_adds_structural_error_when_report_has_no_task_errors(
    monkeypatch,
):
    resource = factories.Resource(
        format="CSV", url_type="", url="https://example.com/structural.csv"
    )
    sysadmin = factories.Sysadmin()

    class StructuralResource(DummyResource):
        def validate(self):
            return DummyReport(valid=False, tasks=[])

    monkeypatch.setattr(validate_action, "Resource", StructuralResource)

    result = validate_action.resource_validate(
        {"user": sysadmin["name"]}, {"id": resource["id"]}
    )

    assert result["id"] == resource["id"]

    record = Validation.get_latest(resource["id"])
    assert record.status == "failure"
    assert record.error_count == 1
    assert record.errors == [
        {
            "type": "structure-error",
            "title": "Structural validation error",
            "description": "The validator could not extract row-level errors from the report.",
            "message": "Structural validation error",
            "rowNumber": None,
            "rowNumbers": [],
            "fieldName": None,
            "fieldNumber": None,
            "cells": [],
            "labels": [],
        }
    ]


def test_resource_validate_wraps_frictionless_exceptions(monkeypatch):
    resource = factories.Resource(
        format="CSV", url_type="", url="https://example.com/boom.csv"
    )
    sysadmin = factories.Sysadmin()

    class BrokenResource(DummyResource):
        def validate(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(validate_action, "Resource", BrokenResource)

    with pytest.raises(toolkit.ValidationError) as exc:
        validate_action.resource_validate(
            {"user": sysadmin["name"]}, {"id": resource["id"]}
        )

    assert exc.value.error_dict == {
        "frictionless": ["System error: boom"]
    }


def test_resource_validation_show_returns_latest_record():
    resource = factories.Resource(format="CSV")
    sysadmin = factories.Sysadmin()

    Validation.create(
        resource_id=resource["id"],
        status="failure",
        error_count=1,
        errors=[{"message": "bad row"}],
    )

    result = validate_action.resource_validation_show(
        {"user": sysadmin["name"]}, {"id": resource["id"]}
    )

    assert result["resource_id"] == resource["id"]
    assert result["status"] == "failure"
    assert result["error_count"] == 1
    assert result["errors"] == [{"message": "bad row"}]


def test_resource_validation_show_raises_not_authorized(monkeypatch):
    def fake_check_access(name, context, data_dict):
        raise toolkit.NotAuthorized()

    monkeypatch.setattr(validate_action.toolkit, "check_access", fake_check_access)

    with pytest.raises(toolkit.NotAuthorized):
        validate_action.resource_validation_show({}, {"id": "res-show"})


def test_resource_validation_show_raises_not_found_when_missing():
    resource = factories.Resource(format="CSV")
    sysadmin = factories.Sysadmin()

    with pytest.raises(
        toolkit.ObjectNotFound,
        match="No validation found for resource",
    ):
        validate_action.resource_validation_show(
            {"user": sysadmin["name"]}, {"id": resource["id"]}
        )


def test_resource_validate_with_real_frictionless_fixture_file():
    resource = factories.Resource(
        format="CSV",
        url_type="",
        url=(FIXTURES_DIR / "so-wrong.csv").resolve().as_uri(),
    )
    sysadmin = factories.Sysadmin()

    result = validate_action.resource_validate(
        {"user": sysadmin["name"]}, {"id": resource["id"]}
    )

    assert result["id"] == resource["id"]

    record = Validation.get_latest(resource["id"])
    assert record is not None
    assert record.status == "failure"
    assert record.error_count >= 1
    assert isinstance(record.errors, list)
    assert record.errors


def test_resource_validate_with_bike_errors_fixture():
    resource = factories.Resource(
        format="CSV",
        url_type="",
        url=(FIXTURES_DIR / "bike-errors.csv").resolve().as_uri(),
    )
    sysadmin = factories.Sysadmin()

    result = validate_action.resource_validate(
        {"user": sysadmin["name"]}, {"id": resource["id"]}
    )

    assert result["id"] == resource["id"]

    record = Validation.get_latest(resource["id"])
    assert record is not None
    assert record.status == "failure"
    assert record.error_count >= 1

    blank_row_error = next(
        (
            err
            for err in (record.errors or [])
            if err.get("rowNumber") == 22
            and "blank" in err.get("message", "").lower()
        ),
        None,
    )
    assert blank_row_error is not None, record.errors


def test_resource_validate_with_so_wrong_fixture():
    resource = factories.Resource(
        format="CSV",
        url_type="",
        url=(FIXTURES_DIR / "so-wrong.csv").resolve().as_uri(),
    )
    sysadmin = factories.Sysadmin()

    result = validate_action.resource_validate(
        {"user": sysadmin["name"]}, {"id": resource["id"]}
    )

    assert result["id"] == resource["id"]

    record = Validation.get_latest(resource["id"])
    assert record is not None
    assert record.status == "failure"
    assert record.error_count >= 1

    messages = [err.get("message", "").lower() for err in (record.errors or [])]
    assert any("header" in msg or "label in the header" in msg for msg in messages)
    assert any(err.get("rowNumber") == 5 for err in (record.errors or []))


# ---------------------------------------------------------------------------
# validation_job_list
# ---------------------------------------------------------------------------

def test_validation_job_list_returns_all_jobs(make_validation_job):
    resource = factories.Resource(format="CSV")

    make_validation_job(resource_id=resource["id"], status="finished")
    make_validation_job(resource_id=resource["id"], status="failed")

    result = helpers.call_action("validation_job_list")

    assert len(result) == 2
    assert {r["status"] for r in result} == {"finished", "failed"}


def test_validation_job_list_is_side_effect_free():
    action = toolkit.get_action("validation_job_list")

    assert hasattr(action, "side_effect_free") is True


def test_validation_job_list_filters_by_status(make_validation_job):
    resource = factories.Resource(format="CSV")

    make_validation_job(resource_id=resource["id"], status="finished")
    make_validation_job(resource_id=resource["id"], status="failed")

    result = helpers.call_action("validation_job_list", status="finished")

    assert len(result) == 1
    assert result[0]["status"] == "finished"


def test_validation_job_list_rejects_invalid_status():
    with pytest.raises(toolkit.ValidationError) as exc:
        helpers.call_action("validation_job_list", status="nonexistent")

    assert "status" in exc.value.error_dict


def test_validation_job_list_rejects_non_integer_limit():
    with pytest.raises(toolkit.ValidationError) as exc:
        helpers.call_action("validation_job_list", limit="abc")

    assert "limit" in exc.value.error_dict


@pytest.mark.parametrize("limit", [0, -1])
def test_validation_job_list_rejects_non_positive_limit(limit):
    with pytest.raises(toolkit.ValidationError) as exc:
        helpers.call_action("validation_job_list", limit=limit)

    assert "limit" in exc.value.error_dict


def test_validation_job_list_raises_not_authorized(monkeypatch):
    def fake_check_access(name, context, data_dict):
        raise toolkit.NotAuthorized()

    monkeypatch.setattr(validate_action.toolkit, "check_access", fake_check_access)

    with pytest.raises(toolkit.NotAuthorized):
        validate_action.validation_job_list({}, {})


def test_validation_job_list_returns_expected_fields(make_validation_job):
    resource = factories.Resource(format="CSV")

    make_validation_job(resource_id=resource["id"], status="finished")

    result = helpers.call_action("validation_job_list")

    assert len(result) == 1
    job = result[0]
    assert set(job.keys()) == {"id", "resource_id", "status", "created", "finished"}
    assert job["resource_id"] == resource["id"]
    assert job["status"] == "finished"


def test_resource_validate_marks_null_like_values_as_failure(tmp_path):
    csv_file = tmp_path / "null-values.csv"
    csv_file.write_text(
        "name,observacion,empty_allowed\n"
        "Alice,null,\n"
        "Bob,   ,   \n"
        "Carla,None,text\n"
        "Dora,NULL,text\n",
        encoding="utf-8",
    )

    resource = factories.Resource(
        format="CSV",
        url_type="",
        url=csv_file.resolve().as_uri(),
    )
    sysadmin = factories.Sysadmin()

    result = validate_action.resource_validate(
        {"user": sysadmin["name"]}, {"id": resource["id"]}
    )

    assert result["id"] == resource["id"]

    record = Validation.get_latest(resource["id"])
    assert record is not None
    assert record.status == "failure"

    null_errors = [
        error
        for error in record.errors
        if error.get("type") == "invalid-null-value"
    ]

    assert len(null_errors) == 3
    assert {error["rowNumber"] for error in null_errors} == {2, 4, 5}
    assert {error["fieldName"] for error in null_errors} == {"observacion"}
