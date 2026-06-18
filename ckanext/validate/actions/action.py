import logging

from frictionless import system, Resource
from ckan.lib import uploader

import ckan.plugins.toolkit as toolkit

from ckanext.validate import helpers as h
from ckanext.validate.model import Validation
from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob
from ckanext.validate.resource_hooks import is_csv_resource


log = logging.getLogger(__name__)


def resource_validate(context, data_dict):
    """Validate a CSV resource using frictionless and store the result.

    :param id: the id of the resource to validate
    :type id: string

    :returns: the resource dict
    :rtype: dict
    """
    resource_id = toolkit.get_or_bust(data_dict, "id")
    toolkit.check_access("resource_update", context, {"id": resource_id})
    resource = toolkit.get_action("resource_show")(context, {"id": resource_id})

    if not is_csv_resource(resource):
        raise toolkit.ValidationError(
            {"format": [toolkit._("Only CSV resources can be validated.")]}
        )

    is_uploaded = resource.get("url_type") == "upload"
    fmt_lower = h.normalize_format(resource)
    if is_uploaded:
        # TODO: Refactor to new file API when migrating to CKAN 2.12.
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

    error_details = h.collect_report_errors(report)
    invalid_null_errors = h.detect_invalid_null_values(source)

    if invalid_null_errors:
        log.info(
            "Invalid null-like values found for resource %s: errors=%d",
            resource_id,
            len(invalid_null_errors),
        )
        error_details.extend(invalid_null_errors)

    status = "success" if report.valid and not invalid_null_errors else "failure"
    error_count = len(error_details)

    Validation.create(
        resource_id=resource_id,
        status=status,
        error_count=error_count,
        errors=error_details,
    )

    log.info(
        "Resource %s validation finished: status=%s errors=%d",
        resource_id, status, error_count,
    )

    return resource


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


@toolkit.side_effect_free
def validation_job_list(context, data_dict):
    """Return a list of validation jobs.

    Restricted to sysadmins.

    :param status: (optional) filter by job status. Must be one of the valid
        :class:`~ckanext.validate.model.validation_jobs.JobStatus` values.
    :type status: string

    :param limit: (optional) maximum number of jobs to return
    :type limit: int

    :returns: list of job dicts
    :rtype: list[dict]
    """
    toolkit.check_access("validation_job_list", context, data_dict)

    valid_statuses = {s.value for s in JobStatus}

    status = data_dict.get("status", "").strip() or None
    if status and status not in valid_statuses:
        raise toolkit.ValidationError(
            {"status": [toolkit._("Invalid job status. Valid values are: {0}").format(
                ", ".join(sorted(valid_statuses))
            )]}
        )

    try:
        limit = int(data_dict.get("limit", 100))
    except (TypeError, ValueError):
        raise toolkit.ValidationError({"limit": [toolkit._("Must be an integer.")]})

    if limit < 1:
        raise toolkit.ValidationError(
            {"limit": [toolkit._("Must be a positive integer.")]}
        )

    jobs = ValidationJob.get_all(status=status, limit=limit)
    return [job.as_dict() for job in jobs]


@toolkit.side_effect_free
def resource_validation_status(context, data_dict):
    resource_id = toolkit.get_or_bust(data_dict, "id")

    toolkit.check_access(
        "resource_validation_status",
        context,
        {"id": resource_id},
    )

    resource = toolkit.get_action("resource_show")(
        {"ignore_auth": True},
        {"id": resource_id},
    )

    record = Validation.get_latest(resource_id)
    job_status = ValidationJob.get_latest_job_status_for_resource(resource_id)
    state = h.get_resource_validation_state(resource) or "not_validated"

    return {
        "resource_id": resource_id,
        "state": state,
        "job_status": job_status,
        "error_count": record.error_count if record else 0,
        "validation": record.as_dict() if record else None,
    }
