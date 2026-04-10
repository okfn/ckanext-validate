import logging

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


def handle_resource_change(context, resource_dict, operation):
    """
    Step 1 only:
    detect whether a created/updated resource is a CSV candidate for
    future automatic validation.

    This function intentionally does not:
    - patch validation fields
    - enqueue jobs
    - run validation
    """
    if not is_resource_eligible_for_auto_validation(resource_dict):
        log.debug(
            "Skipping auto-validation detection for resource %s on %s "
            "(format=%r, state=%r, url_type=%r)",
            resource_dict.get("id"),
            operation,
            resource_dict.get("format"),
            resource_dict.get("state"),
            resource_dict.get("url_type"),
        )
        return False

    log.info(
        "Auto-validation candidate detected on resource_%s: "
        "id=%s format=%s url_type=%s url=%s",
        operation,
        resource_dict.get("id"),
        resource_dict.get("format"),
        resource_dict.get("url_type"),
        resource_dict.get("url"),
    )

    return True
