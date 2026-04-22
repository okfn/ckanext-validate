import logging

import ckan.plugins.toolkit as toolkit

from ckanext.validate import jobs
from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob

log = logging.getLogger(__name__)


def is_csv_resource(resource_dict):
    fmt = (resource_dict.get("format") or "").strip().lower()
    return fmt == "csv"


def is_resource_eligible_for_auto_validation(resource_dict):
    if not resource_dict:
        return False

    if not resource_dict.get("id"):
        return False

    if resource_dict.get("state") == "deleted":
        return False

    if not is_csv_resource(resource_dict):
        return False

    return True


def build_validation_job_id(resource_id):
    return f"validate-resource-{resource_id}"


def enqueue_resource_validation_job(resource_id):
    latest_status = ValidationJob.get_latest_job_status_for_resource(resource_id)

    if latest_status in JobStatus.pending_statuses():
        log.debug(
            "Validation job already pending for resource %s (status=%s), skipping enqueue",
            resource_id,
            latest_status,
        )
        return None

    # Crear el registro ANTES de encolar para que la UI pueda mostrar Pending
    ValidationJob.create(resource_id=resource_id, status=JobStatus.QUEUED)

    try:
        return toolkit.enqueue_job(
            jobs.run_resource_validation_job,
            args=[resource_id],
            title=f"Validate resource {resource_id}",
            rq_kwargs={"job_id": build_validation_job_id(resource_id)},
        )
    except Exception:
        # Mantener el estado queued si el job ya estaba en cola con el mismo job_id
        log.debug("Validation job already enqueued for resource %s, skipping", resource_id)
        return None


def handle_resource_change(resource_dict):
    if not is_resource_eligible_for_auto_validation(resource_dict):
        log.debug(
            "Skipping auto-validation flow for resource %s "
            "(format=%r, state=%r, url_type=%r)",
            resource_dict.get("id") if resource_dict else None,
            resource_dict.get("format") if resource_dict else None,
            resource_dict.get("state") if resource_dict else None,
            resource_dict.get("url_type") if resource_dict else None,
        )
        return False

    resource_id = resource_dict["id"]
    enqueue_resource_validation_job(resource_id)

    log.info("Validation job enqueued for resource %s", resource_id)
    return True
