import json
import logging

from frictionless import system, Resource
from ckan.lib import uploader

import ckan.plugins.toolkit as toolkit

from ckanext.validate.model import Validation

log = logging.getLogger(__name__)


def resource_validate(context, data_dict):
    """Validate a CSV resource using frictionless and store the result.

    :param id: the id of the resource to validate
    :type id: string

    :returns: resource dict with updated validation_status and
              validation_error_count fields
    :rtype: dict
    """
    resource_id = toolkit.get_or_bust(data_dict, "id")
    toolkit.check_access("resource_update", context, {"id": resource_id})
    resource = toolkit.get_action("resource_show")(context, {"id": resource_id})

    fmt = (resource.get("format") or "").upper()
    if fmt != "CSV":
        raise toolkit.ValidationError(
            {"format": [toolkit._("Only CSV resources can be validated.")]}
        )

    is_uploaded = resource.get("url_type") == "upload"
    fmt_lower = (resource.get("format") or "").lower()
    if is_uploaded:
        upload = uploader.get_resource_uploader(resource)
        source = "file://" + upload.get_path(resource["id"])
    else:
        source = resource["url"]

    log.info(
        "Starting validation for resource %s (format=%s, uploaded=%s, source=%s)",
        resource_id, fmt_lower, is_uploaded, source,
    )

    try:
        if is_uploaded:
            with system.use_context(trusted=True):
                res = Resource(source, format=fmt_lower)
                report = res.validate()
        else:
            res = Resource(source, format=fmt_lower)
            report = res.validate()

    except Exception as exc:
        log.exception("Frictionless raised an exception for resource %s", resource_id)
        raise toolkit.ValidationError(
            {"frictionless": [toolkit._("System error: {0}").format(str(exc))]}
        )

    log.info(
        "Frictionless validation completed for resource %s: valid=%s",
        resource_id, report.valid,
    )
    log.debug("Validation report for resource %s: %s", resource_id, report.to_descriptor())

    status = "success" if report.valid else "failure"

    errors = []
    for task in report.tasks:
        errors.extend(task.errors)

    error_details = [
        {
            "row": getattr(err, "row_number", None),
            "field": getattr(err, "field_name", None),
            "message": err.message,
        }
        for err in errors
    ]

    if not report.valid and not error_details:
        error_details.append({
            "message": toolkit._("Structural validation error"),
            "code": "structure-error",
        })

    error_count = len(error_details)

    # Persist result in dedicated table
    Validation.create(
        resource_id=resource_id,
        status=status,
        error_count=error_count,
        errors=error_details,
    )

    updated_resource = toolkit.get_action("resource_patch")(
        {"ignore_auth": True},
        {
            "id": resource_id,
            "validation_status": status,
            "validation_error_count": error_count,
            "validation_errors": json.dumps(error_details),
        },
    )

    log.info(
        "Resource %s validation finished: status=%s errors=%d",
        resource_id, status, error_count,
    )

    return updated_resource


def resource_validation_show(context, data_dict):
    """Return the latest validation result for a resource.

    :param id: the id of the resource
    :type id: string

    :returns: dict with validation result or raises ObjectNotFound
    :rtype: dict
    """
    resource_id = toolkit.get_or_bust(data_dict, "id")
    toolkit.check_access("resource_show", context, {"id": resource_id})

    record = Validation.get_latest(resource_id)

    if record is None:
        raise toolkit.ObjectNotFound(
            toolkit._("No validation found for resource {0}").format(resource_id)
        )

    return record.as_dict()
