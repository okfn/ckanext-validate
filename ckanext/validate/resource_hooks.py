
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


def mark_resource_as_pending(resource_id):
    log.info("Marking resource %s as pending", resource_id)
    patch_context = {
        "ignore_auth": True,
        _VALIDATE_INTERNAL_PATCH_FLAG: True,
    }
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
    return toolkit.enqueue_job(
        jobs.run_resource_validation_job,
        args=[resource_id, username],
        title=f"Validate resource {resource_id}",
        queue="validate",
    )


def handle_resource_change(context, resource_dict, operation):
    """
    This function intentionally does not:
    - run validation
    - patch final validation results
    - modify the UI
    """
    context = context or {}

    log.info(
        "handle_resource_change op=%s resource_id=%s format=%s url_type=%s user=%r",
        operation,
        resource_dict.get("id"),
        resource_dict.get("format"),
        resource_dict.get("url_type"),
        context.get("user"),
    )

    if context.get(_VALIDATE_INTERNAL_PATCH_FLAG):
        log.info(
            "Skipping internal validation patch for resource %s on %s",
            resource_dict.get("id") if resource_dict else None,
            operation,
        )
        return False

    if not is_resource_eligible_for_auto_validation(resource_dict):
        log.debug(
            "Skipping auto-validation flow for resource %s on %s "
            "(format=%r, state=%r, url_type=%r)",
            resource_dict.get("id"),
            operation,
            resource_dict.get("format"),
            resource_dict.get("state"),
            resource_dict.get("url_type"),
        )
        return False

    username = context.get("user")
    resource_id = resource_dict["id"]

    log.info("Marking resource %s as pending", resource_id)
    mark_resource_as_pending(resource_id)

    log.info("Enqueuing validation job for resource %s user=%r", resource_id, username)
    enqueue_resource_validation_job(resource_id, username)

    log.info(
        "Resource %s marked as pending and validation job enqueued after resource_%s",
        resource_id,
        operation,
    )

    return True
