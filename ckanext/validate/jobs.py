import json
import logging
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)


"""
Con esta comando, para procesar la cola de validación usar:

ckan -c /etc/ckan/default/ckan.ini jobs worker validate

Y si querés escuchar default y validate a la vez:

ckan -c /etc/ckan/default/ckan.ini jobs worker default validate

https://docs.ckan.org/en/2.11/maintaining/cli.html

"""


def patch_resource_validation_error(resource_id, message):
    toolkit.get_action("resource_patch")(
        {"ignore_auth": True},
        {
            "id": resource_id,
            "validation_status": "error",
            "validation_error_count": None,
            "validation_errors": json.dumps(
                [
                    {
                        "message": message,
                    }
                ]
            ),
        },
    )


def run_resource_validation_job(resource_id):
    """
    Step 5:
    execute validation in the background job and ensure the resource
    is updated with a final result, including the error case.
    """
    log.info("Starting background validation for resource %s", resource_id)

    try:
        toolkit.get_action("resource_validate")(
            {"ignore_auth": True},
            {"id": resource_id},
        )
        log.info("Finished background validation for resource %s", resource_id)

    except Exception as exc:
        log.exception(
            "Background validation failed for resource %s",
            resource_id,
        )

        patch_resource_validation_error(
            resource_id,
            toolkit._("System error: {0}").format(str(exc)),
        )

        raise
