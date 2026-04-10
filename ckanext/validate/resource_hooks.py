import logging
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

_INTERNAL_PENDING_PATCH_FLAG = "_validate_internal_pending_patch"


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
    toolkit.get_action("resource_patch")(
        {
            "ignore_auth": True,
            _INTERNAL_PENDING_PATCH_FLAG: True,
        },
        {
            "id": resource_id,
            "validation_status": "pending",
            "validation_error_count": None,
            "validation_errors": None,
        },
    )


def handle_resource_change(context, resource_dict, operation):
    """
    Step 2 only:
    mark eligible CSV resources as pending right after create/update.

    This function intentionally does not:
    - enqueue jobs
    - run validation
    - modify the UI
    """
    context = context or {}

    # Avoid re-entering the hook when our own internal resource_patch runs
    if context.get(_INTERNAL_PENDING_PATCH_FLAG):
        log.debug(
            "Skipping pending patch hook re-entry for resource %s on %s",
            resource_dict.get("id") if resource_dict else None,
            operation,
        )
        return False

    if not is_resource_eligible_for_auto_validation(resource_dict):
        log.debug(
            "Skipping pending status for resource %s on %s "
            "(format=%r, state=%r, url_type=%r)",
            resource_dict.get("id"),
            operation,
            resource_dict.get("format"),
            resource_dict.get("state"),
            resource_dict.get("url_type"),
        )
        return False

    mark_resource_as_pending(resource_dict["id"])

    log.info(
        "Resource %s marked as pending after resource_%s "
        "(format=%s, url_type=%s, url=%s)",
        resource_dict.get("id"),
        operation,
        resource_dict.get("format"),
        resource_dict.get("url_type"),
        resource_dict.get("url"),
    )

    return True
