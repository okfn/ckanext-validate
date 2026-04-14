import logging

import ckan.plugins.toolkit as toolkit

from ckanext.validate import jobs

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
    try:
        return toolkit.enqueue_job(
            jobs.run_resource_validation_job,
            args=[resource_id],
            title=f"Validate resource {resource_id}",
            rq_kwargs={"job_id": build_validation_job_id(resource_id)},
        )
    except Exception:
        log.debug("Validation job already enqueued for resource %s, skipping", resource_id)
        return None


def handle_resource_change(context, resource_dict, operation):
    if not is_resource_eligible_for_auto_validation(resource_dict):
        log.debug(
            "Skipping auto-validation flow for resource %s on %s "
            "(format=%r, state=%r, url_type=%r)",
            resource_dict.get("id") if resource_dict else None,
            operation,
            resource_dict.get("format") if resource_dict else None,
            resource_dict.get("state") if resource_dict else None,
            resource_dict.get("url_type") if resource_dict else None,
        )
        return False

    resource_id = resource_dict["id"]
    enqueue_resource_validation_job(resource_id)

    log.info(
        "Validation job enqueued for resource %s after resource_%s",
        resource_id,
        operation,
    )
    return True
