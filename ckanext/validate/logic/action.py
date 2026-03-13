import logging

import frictionless

import ckan.plugins.toolkit as toolkit

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

    source = resource["url"]
    log.debug("Validating resource %s from %s", resource_id, source)

    try:
        report = frictionless.validate(source)
    except Exception as exc:
        log.error("Frictionless raised an exception for resource %s: %s", resource_id, exc)
        patch_data = {
            "id": resource_id,
            "validation_status": "error",
            "validation_error_count": 0,
        }
        return toolkit.get_action("resource_patch")({"ignore_auth": True}, patch_data)

    status = "success" if report.valid else "failure"
    error_count = sum(len(table.errors) for table in report.tasks)

    patch_data = {
        "id": resource_id,
        "validation_status": status,
        "validation_error_count": error_count,
    }

    updated_resource = toolkit.get_action("resource_patch")(
        {"ignore_auth": True}, patch_data
    )

    log.info(
        "Resource %s validation finished: status=%s errors=%d",
        resource_id,
        status,
        error_count,
    )

    return updated_resource
