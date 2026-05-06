from ckanext.validate.model.validation import Validation
from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob


def get_resource_validation_job_status(resource_dict):
    if not resource_dict:
        return None

    resource_id = resource_dict.get("id")
    if not resource_id:
        return None

    return ValidationJob.get_latest_job_status_for_resource(resource_id)


def get_resource_validation_state(resource_dict):
    if not resource_dict:
        return None

    status = Validation.get_resource_status(resource_dict.get("id"))
    if status:
        return status

    job_status = get_resource_validation_job_status(resource_dict)
    if job_status in JobStatus.pending_statuses():
        return "pending"

    if job_status in JobStatus.running_statuses():
        return "running"

    if job_status in JobStatus.error_statuses():
        return "error"

    return None
