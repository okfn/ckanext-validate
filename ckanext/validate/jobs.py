import logging

import ckan.plugins.toolkit as toolkit

from ckanext.validate.model import Validation

log = logging.getLogger(__name__)


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

    try:
        toolkit.get_action("resource_validate")(
            context,
            {"id": resource_id},
        )
        log.info("Finished background validation for resource %s", resource_id)

    except Exception as exc:
        log.exception(
            "Background validation failed for resource %s",
            resource_id,
        )

        Validation.create(
            resource_id=resource_id,
            status="error",
            error_count=0,
            errors=[{"message": toolkit._("System error: {0}").format(str(exc))}],
        )

        raise
