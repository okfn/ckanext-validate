import logging

import ckan.plugins.toolkit as toolkit

from ckanext.validate import jobs

log = logging.getLogger(__name__)

_VALIDATE_INTERNAL_PATCH_FLAG = "_validate_internal_patch"


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


def mark_resource_as_pending(resource_id, username=None):
    patch_context = {
        "ignore_auth": True,
        _VALIDATE_INTERNAL_PATCH_FLAG: True,
    }
    if username:
        patch_context["user"] = username

    log.info("Marking resource %s as pending", resource_id)
    toolkit.get_action("resource_patch")(
        patch_context,
        {
            "id": resource_id,
            "validation_status": "pending",
            "validation_error_count": None,
            "validation_errors": None,
        },
    )


def enqueue_resource_validation_job(resource_id, username=None):
    log.info("Enqueuing validation job for resource %s user=%r", resource_id, username)
    try:
        return toolkit.enqueue_job(
            jobs.run_resource_validation_job,
            args=[resource_id, username],
            title=f"Validate resource {resource_id}",
            rq_kwargs={"job_id": build_validation_job_id(resource_id)},
        )
    except Exception:
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
    username = resource_dict.get("user")
    mark_resource_as_pending(resource_id, username)
    enqueue_resource_validation_job(resource_id, username)

    log.info("Validation job enqueued for resource %s", resource_id)
    return True
