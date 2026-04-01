
import json
import logging
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

_VALIDATE_INTERNAL_PATCH_FLAG = "_validate_internal_patch"


"""
Con esta comando, para procesar la cola de validación usar:

ckan -c /etc/ckan/default/ckan.ini jobs worker validate

Y si querés escuchar default y validate a la vez:

ckan -c /etc/ckan/default/ckan.ini jobs worker default validate

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

    try:
        toolkit.get_action("resource_validate")(
            action_context,
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
            username=username,
        )

        raise
