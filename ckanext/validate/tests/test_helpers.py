import pytest

from ckanext.validate import helpers
from ckanext.validate.model.validation import Validation
from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob
from ckanext.validate.tests.conftest import status_value
from ckanext.validate import helpers as h


@pytest.mark.parametrize("job_status", list(JobStatus.error_statuses()))
def test_get_resource_validation_state_returns_error_for_any_error_job_status(job_status):
    resource_id = f"res-error-{job_status.value}"

    ValidationJob.create(resource_id=resource_id, status=job_status)

    assert helpers.get_resource_validation_state({"id": resource_id}) == "error"


@pytest.mark.parametrize("job_status", list(JobStatus.pending_statuses()))
def test_get_resource_validation_state_returns_pending_for_any_pending_job_status(job_status):
    resource_id = f"res-pending-{job_status.value}"

    ValidationJob.create(resource_id=resource_id, status=job_status)

    assert helpers.get_resource_validation_state({"id": resource_id}) == "pending"


def test_get_resource_validation_job_status_returns_none_without_resource():
    assert helpers.get_resource_validation_job_status(None) is None
    assert helpers.get_resource_validation_job_status({}) is None
    assert helpers.get_resource_validation_job_status({"name": "no-id"}) is None


def test_get_resource_validation_state_returns_pending_when_pending_job_exists_even_with_success_validation():
    resource_id = "res-success-over-pending"

    Validation.create(
        resource_id=resource_id,
        status="success",
        error_count=0,
        errors=[],
    )
    ValidationJob.create(resource_id=resource_id, status=JobStatus.QUEUED)

    assert helpers.get_resource_validation_state({"id": resource_id}) == "pending"


def test_get_resource_validation_state_returns_running_when_running_job_exists_even_with_failure_validation():
    resource_id = "res-failure-over-running"

    Validation.create(
        resource_id=resource_id,
        status="failure",
        error_count=2,
        errors=[{"message": "bad row"}],
    )
    ValidationJob.create(resource_id=resource_id, status=JobStatus.RUNNING)

    assert helpers.get_resource_validation_state({"id": resource_id}) == "running"


def test_get_resource_validation_state_returns_pending_when_no_validation_and_job_is_pending():
    resource_id = "res-pending"

    ValidationJob.create(resource_id=resource_id, status=JobStatus.QUEUED)

    assert helpers.get_resource_validation_state({"id": resource_id}) == "pending"


def test_get_resource_validation_state_returns_error_when_no_validation_and_job_is_error():
    resource_id = "res-error"

    ValidationJob.create(resource_id=resource_id, status=JobStatus.ERROR)

    assert helpers.get_resource_validation_state({"id": resource_id}) == "error"


def test_get_resource_validation_state_returns_none_when_no_validation_or_job():
    assert helpers.get_resource_validation_state(None) is None
    assert helpers.get_resource_validation_state({}) is None
    assert helpers.get_resource_validation_state({"id": "missing-resource"}) is None


def test_get_resource_validation_job_status_returns_latest_job_status():
    resource_id = "res-latest-job-status"

    ValidationJob.create(resource_id=resource_id, status=JobStatus.ERROR)
    ValidationJob.create(resource_id=resource_id, status=JobStatus.RUNNING)

    status = helpers.get_resource_validation_job_status({"id": resource_id})

    assert status_value(status) == "running"


def test_group_validation_errors_merges_preview_rows_with_multiple_column_errors():
    errors = [
        {
            "type": "type-error",
            "title": "Type Error",
            "message": "Column 2 is invalid",
            "rowNumber": 12,
            "fieldNumber": 2,
            "cells": ["501247-540", "bad", "501247", "also bad"],
        },
        {
            "type": "type-error",
            "title": "Type Error",
            "message": "Column 4 is invalid",
            "rowNumber": 12,
            "fieldNumber": 4,
            "cells": ["501247-540", "bad", "501247", "also bad"],
        },
        {
            "type": "type-error",
            "title": "Type Error",
            "message": "Column 3 is invalid",
            "rowNumber": 13,
            "fieldNumber": 3,
            "cells": ["501247-541", "ok", "bad", "ok"],
        },
    ]

    groups = h.group_validation_errors(errors)

    preview_rows = groups[0]["preview"]["rows"]

    assert [row["row_number"] for row in preview_rows] == [12, 13]
    assert preview_rows[0]["highlight_columns"] == [2, 4]
    assert preview_rows[1]["highlight_columns"] == [3]
