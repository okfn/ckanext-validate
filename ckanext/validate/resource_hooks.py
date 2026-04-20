import logging
import os
import tempfile

import ckan.plugins.toolkit as toolkit
from frictionless import Resource as FrictionlessResource, system

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
