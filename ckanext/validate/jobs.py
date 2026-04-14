import logging

import ckan.plugins.toolkit as toolkit

from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob

log = logging.getLogger(__name__)

_VALIDATE_INTERNAL_PATCH_FLAG = "_validate_internal_patch"


"""
To process the background jobs queue, use the following command:

ckan -c /etc/ckan/default/ckan.ini jobs worker

https://docs.ckan.org/en/2.11/maintaining/cli.html

"""


def run_resource_validation_job(resource_id):
    """
    Step 5:
    execute validation in the background job and ensure the resource
    is updated with a final result, including the error case.
    """
    log.info("Starting background validation for resource %s", resource_id)

    site_user = toolkit.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"ignore_auth": True, "user": site_user["name"]}

    ValidationJob.create(resource_id=resource_id, status=JobStatus.RUNNING)
    try:
        toolkit.get_action("resource_validate")(
            context,
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
