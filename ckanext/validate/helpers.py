from ckanext.validate.model.validation import Validation
from ckanext.validate.model.validation_jobs import ValidationJob


PENDING_JOB_STATUSES = {"queued", "started", "deferred", "scheduled"}
ERROR_JOB_STATUSES = {"failed", "stopped", "canceled"}


def get_resource_validation_job_status(resource_dict):
    if not resource_dict:
        return None

    resource_id = resource_dict.get("id")
    if not resource_id:
        return None

    status = ValidationJob.get_latest_job_status_for_resource(resource_id)

    return status


def get_resource_validation_state(resource_dict):
    if not resource_dict:
        return None

    status = Validation.get_resource_status(resource_dict.get("id"))
    if status:
        return status

    job_status = get_resource_validation_job_status(resource_dict)
    if job_status in PENDING_JOB_STATUSES:
        return "pending"

    if job_status in ERROR_JOB_STATUSES:
        return "error"

    return None
