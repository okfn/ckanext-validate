import logging
import json

import ckan.plugins.toolkit as toolkit

from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob

log = logging.getLogger(__name__)

_VALIDATE_INTERNAL_PATCH_FLAG = "_validate_internal_patch"

"""
To process the background jobs queue, use the following command:

ckan -c /etc/ckan/default/ckan.ini jobs worker

https://docs.ckan.org/en/2.11/maintaining/cli.html

"""


def patch_resource_validation_error(resource_id, message, username=None):
    patch_context = {"ignore_auth": True, _VALIDATE_INTERNAL_PATCH_FLAG: True}
    if username:
        patch_context["user"] = username

    log.info(
        "Patching validation error for resource_id=%s username=%r message=%r",
        resource_id,
        username,
        message,
    )
    log.debug("patch_resource_validation_error context=%r", patch_context)

    toolkit.get_action("resource_patch")(
        patch_context,
        {
            "id": resource_id,
            "validation_status": "error",
            "validation_error_count": None,
            "validation_errors": json.dumps([
                {
                    "message": message,
                }
            ]),
        },
    )


def run_resource_validation_job(resource_id, username=None):
    """
    Step 5:
    execute validation in the background job and ensure the resource
    is updated with a final result, including the error case.
    """
    log.info("run_resource_validation_job start resource_id=%s username=%r", resource_id, username)

    action_context = {"ignore_auth": True}
    if username:
        action_context["user"] = username

    log.info(
        "Calling resource_validate for resource_id=%s with context=%r",
        resource_id,
        action_context,
    )

    ValidationJob.create(resource_id=resource_id, status=JobStatus.RUNNING)
    try:
        toolkit.get_action("resource_validate")(
            action_context,
            {"id": resource_id},
        )
        log.info("Finished background validation for resource %s", resource_id)
        ValidationJob.update(resource_id=resource_id, status=JobStatus.FINISHED)

    except ValueError as exc:
        log.error(
            "No existing validation job found for resource %s when trying to update status: %s",
            resource_id,
            str(exc),
        )
        ValidationJob.update(resource_id=resource_id, status=JobStatus.ERROR)

    except Exception:
        log.exception(
            "Background validation failed for resource %s",
            resource_id,
        )

        ValidationJob.create(resource_id=resource_id, status=JobStatus.ERROR)
