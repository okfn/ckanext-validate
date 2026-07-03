import logging

from frictionless import system, Resource
from ckan.lib import uploader

import ckan.plugins.toolkit as toolkit

from ckanext.validate import helpers as h
from ckanext.validate.model import Validation
from ckanext.validate.model.validation_configuration import (
    ValidationConfiguration,
)
from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob
from ckanext.validate.resource_hooks import is_csv_resource
from ckanext.validate.detector import ValidateDetector


log = logging.getLogger(__name__)


def get_validation_report(source, resource_format, schema=None):
    """Main function to execute and and get the validation report.

    The validation process is opinionated to reflect end users requirements
    and expected UX in common validation scenarios.

    Opinionated rules:
        1. Improve accuracy on integer columns. Frictionless is to aggresive
        on casting numeric columns into string as soon as a few string appears.
        We want to be more permissive and detect it as integer even if a few
        cells contains strings.
        2. We are setting some common missing values for string columns.
        3. We force required on all columns, this is required to detect values
        from point number 2 as errors.

    This opinionated values could be ease with some UI elements that allows custom
    schemas, but for now we want to keep it simple.

    Returns:
        A Frictionless report.
    """
    log.debug("00000000000000000000Getting validation report for source=%s, resource_format=%s, schema=%s",
              source, resource_format, schema)

    detector = ValidateDetector(
        field_missing_values=[
            "null",
            "NULL",
            "None",
        ],
        field_confidence=0.5,
    )

    with system.use_context(trusted=True):
        resource = Resource(
            source,
            format=resource_format,
            detector=detector,
        )

        resource.infer()

        if schema is not None:
            resource.schema = h.merge_validation_schema(
                resource.schema,
                schema,
            )
        else:
            for field in resource.schema.fields:
                constraints = dict(
                    field.constraints or {}
                )

                constraints["required"] = True
                field.constraints = constraints

        return resource.validate()


def resource_validate(context, data_dict):
    """Validate a CSV resource using frictionless and store the result.

    :param id: the id of the resource to validate
    :type id: string

    :returns: the resource dict
    :rtype: dict
    """
    log.debug("11111111111111111Validating resource with data_dict=%s", data_dict)

    resource_id = toolkit.get_or_bust(data_dict, "id")
    toolkit.check_access("resource_update", context, {"id": resource_id})
    resource = toolkit.get_action("resource_show")(context, {"id": resource_id})

    if not is_csv_resource(resource):
        raise toolkit.ValidationError(
            {"format": [toolkit._("Only CSV resources can be validated.")]}
        )

    configuration_id = data_dict.get("validation_configuration_id")

    if configuration_id:
        configuration = ValidationConfiguration.get_active(configuration_id)

        if configuration is None:
            raise toolkit.ValidationError(
                {
                    "validation_configuration_id": [
                        toolkit._(
                            "The selected validation configuration "
                            "does not exist or is inactive."
                        )
                    ]
                }
            )
    else:
        configuration = h.get_configuration_for_resource(resource)

    is_uploaded = resource.get("url_type") == "upload"
    resource_format = h.normalize_format(resource)
    if is_uploaded:
        # TODO: Refactor to new file API when migrating to CKAN 2.12.
        upload = uploader.get_resource_uploader(resource)
        source = "file://" + upload.get_path(resource_id)
    else:
        source = resource["url"]

    log.info(
        "Starting validation for resource %s "
        "(format=%s, uploaded=%s, source=%s, "
        "configuration_id=%s, configuration_name=%s)",
        resource_id,
        resource_format,
        is_uploaded,
        source,
        configuration.id if configuration else None,
        configuration.name if configuration else None,
    )

    try:
        configured_schema = (
            configuration.get_schema()
            if configuration
            else None
        )

        report = get_validation_report(
            source,
            resource_format,
            schema=configured_schema,
        )
    except Exception as exc:
        log.exception("Frictionless raised an exception for resource %s", resource_id)
        raise toolkit.ValidationError(
            {"frictionless": [toolkit._("System error: {0}").format(str(exc))]}
        )

    log.info(
        "Frictionless validation completed for resource %s: valid=%s",
        resource_id, report.valid,
    )

    status = "success" if report.valid else "failure"
    error_details = h.collect_report_errors(report)
    error_count = len(error_details)

    Validation.create(
        resource_id=resource_id,
        status=status,
        error_count=error_count,
        errors=error_details,
    )

    log.info(
        "Resource %s validation finished: status=%s errors=%d configuration_id=%s",
        resource_id,
        status,
        error_count,
        configuration.id if configuration else None,
    )

    return resource


def resource_validation_show(context, data_dict):
    """Return the latest validation result for a resource.

    :param id: the id of the resource
    :type id: string

    :returns: dict with validation result or raises ObjectNotFound
    :rtype: dict
    """
    log.debug("22222222222222222Showing validation for resource with data_dict=%s", data_dict)
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
    log.debug("33333333333333333Listing validation jobs with data_dict=%s", data_dict)
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
    log.debug("44444444444444444Getting validation status for resource with data_dict=%s", data_dict)
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
