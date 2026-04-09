
import logging
import os
import tempfile

import ckan.plugins.toolkit as toolkit
from frictionless import Resource as FrictionlessResource, system

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

    mark_resource_as_pending(resource_id, username)
    enqueue_resource_validation_job(resource_id, username)

    log.info(
        "Resource %s marked as pending and validation job enqueued after resource_%s",
        resource_id,
        operation,
    )

    return True


# ---------------------------------------------------------------------------
# Strict-mode: synchronous validation before create/update
# ---------------------------------------------------------------------------

def is_fail_on_invalid_upload_enabled():
    """Return True when the sysadmin has enabled strict CSV-upload validation."""
    return toolkit.asbool(
        toolkit.config.get("ckanext.validate.fail_on_invalid_upload", False)
    )


def validate_csv_upload_strict(data_dict):
    """Synchronously validate a CSV upload and raise ValidationError if invalid.

    Called from ``before_resource_create`` and ``before_resource_update`` when
    ``ckanext.validate.fail_on_invalid_upload`` is ``true``.  Operates on the
    in-memory file object *before* it is written to disk, so an invalid file
    never persists.

    Does nothing when:
    * strict mode is disabled (the default),
    * the resource format is not CSV, or
    * no file upload is present in *data_dict* (e.g. a metadata-only update).
    """
    if not is_fail_on_invalid_upload_enabled():
        return

    fmt = (data_dict.get("format") or "").strip().lower()
    if fmt != "csv":
        return

    upload = data_dict.get("upload")
    if not upload or isinstance(upload, str) or not hasattr(upload, "read"):
        return

    try:
        content = upload.read()
        upload.seek(0)
    except Exception:
        log.warning(
            "validate_csv_upload_strict: could not read upload object — skipping strict validation"
        )
        return

    if not content:
        return

    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as exc:
        log.warning("validate_csv_upload_strict: could not write temp file — skipping: %s", exc)
        return

    try:
        with system.use_context(trusted=True):
            res = FrictionlessResource("file://" + tmp_path, format="csv")
            report = res.validate()
    except Exception as exc:
        raise toolkit.ValidationError(
            {"upload": [toolkit._("System error during validation: {0}").format(str(exc))]}
        )
    finally:
        os.unlink(tmp_path)

    if not report.valid:
        errors = []
        for task in report.tasks:
            errors.extend(task.errors)

        error_messages = [err.message for err in errors]
        if not error_messages:
            error_messages = [toolkit._("Structural validation error")]

        raise toolkit.ValidationError({"upload": error_messages})
