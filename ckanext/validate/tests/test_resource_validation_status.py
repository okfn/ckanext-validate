import pytest

from ckan.tests import factories, helpers

from ckanext.validate.model.validation import Validation
from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob


@pytest.mark.usefixtures("clean_db", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "validate")
def test_resource_validation_status_updates_from_pending_to_success():
    sysadmin = factories.Sysadmin()
    dataset = factories.Dataset(user=sysadmin)
    resource = factories.Resource(
        package_id=dataset["id"],
        format="CSV",
    )

    context = {"user": sysadmin["name"]}

    job = ValidationJob.create(
        resource_id=resource["id"],
        status=JobStatus.QUEUED,
    )

    result = helpers.call_action(
        "resource_validation_status",
        context=context,
        id=resource["id"],
    )

    assert result["state"] == "pending"
    assert result["job_status"] == "queued"
    assert result["validation"] is None

    Validation.create(
        resource_id=resource["id"],
        status="success",
        error_count=0,
        errors=[],
    )

    ValidationJob.update_by_id(job.id, JobStatus.FINISHED)

    result = helpers.call_action(
        "resource_validation_status",
        context=context,
        id=resource["id"],
    )

    assert result["state"] == "success"
    assert result["job_status"] == "finished"
    assert result["validation"]["status"] == "success"
    assert result["error_count"] == 0


@pytest.mark.usefixtures("clean_db", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "validate")
def test_resource_validation_status_prefers_pending_job_over_previous_validation():
    sysadmin = factories.Sysadmin()
    dataset = factories.Dataset(user=sysadmin)
    resource = factories.Resource(
        package_id=dataset["id"],
        format="CSV",
    )

    context = {"user": sysadmin["name"]}

    Validation.create(
        resource_id=resource["id"],
        status="success",
        error_count=0,
        errors=[],
    )

    ValidationJob.create(
        resource_id=resource["id"],
        status=JobStatus.QUEUED,
    )

    result = helpers.call_action(
        "resource_validation_status",
        context=context,
        id=resource["id"],
    )

    assert result["state"] == "pending"
    assert result["job_status"] == "queued"
