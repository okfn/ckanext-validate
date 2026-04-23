import datetime

from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob
from ckanext.validate.tests.conftest import status_value


def test_validation_job_create_stores_status_as_string():
    job = ValidationJob.create(resource_id="res-create-string", status=JobStatus.QUEUED)

    refreshed = ValidationJob.get(job.id)

    assert status_value(refreshed.status) == "queued"
    assert refreshed.finish_timestamp is None


def test_validation_job_update_by_id_sets_finish_timestamp_for_finished():
    job = ValidationJob.create(resource_id="res-finished-ts", status=JobStatus.QUEUED)

    assert job.finish_timestamp is None

    ValidationJob.update_by_id(job.id, JobStatus.FINISHED)

    refreshed = ValidationJob.get(job.id)
    assert status_value(refreshed.status) == "finished"
    assert refreshed.finish_timestamp is not None


def test_validation_job_update_by_id_sets_finish_timestamp_for_error():
    job = ValidationJob.create(resource_id="res-error-ts", status=JobStatus.QUEUED)

    assert job.finish_timestamp is None

    ValidationJob.update_by_id(job.id, JobStatus.ERROR)

    refreshed = ValidationJob.get(job.id)
    assert status_value(refreshed.status) == "error"
    assert refreshed.finish_timestamp is not None


def test_validation_job_update_by_id_does_not_set_finish_timestamp_for_running():
    job = ValidationJob.create(resource_id="res-running-ts", status=JobStatus.QUEUED)

    assert job.finish_timestamp is None

    ValidationJob.update_by_id(job.id, JobStatus.RUNNING)

    refreshed = ValidationJob.get(job.id)
    assert status_value(refreshed.status) == "running"
    assert refreshed.finish_timestamp is None


def test_get_latest_job_for_resource_returns_most_recent_job():
    resource_id = "res-latest-job"

    older = ValidationJob.create(resource_id=resource_id, status=JobStatus.QUEUED)
    newer = ValidationJob.create(resource_id=resource_id, status=JobStatus.RUNNING)

    older.create_timestamp = datetime.datetime(2026, 1, 1, 10, 0, 0)
    older.commit()

    newer.create_timestamp = datetime.datetime(2026, 1, 1, 10, 1, 0)
    newer.commit()

    latest = ValidationJob.get_latest_job_for_resource(resource_id)

    assert latest is not None
    assert latest.id == newer.id
    assert status_value(latest.status) == "running"


def test_get_latest_job_status_for_resource_returns_status_of_most_recent_job():
    resource_id = "res-latest-status"

    older = ValidationJob.create(resource_id=resource_id, status=JobStatus.ERROR)
    newer = ValidationJob.create(resource_id=resource_id, status=JobStatus.FINISHED)

    older.create_timestamp = datetime.datetime(2026, 1, 1, 11, 0, 0)
    older.commit()

    newer.create_timestamp = datetime.datetime(2026, 1, 1, 11, 1, 0)
    newer.commit()

    latest_status = ValidationJob.get_latest_job_status_for_resource(resource_id)

    assert status_value(latest_status) == "finished"
