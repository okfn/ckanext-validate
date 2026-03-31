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


def run_resource_validation_job(resource_id):
    """
    Step 4 only:
    execute validation from the background job by reusing the existing
    resource_validate action.
    """
    log.info("Starting background validation for resource %s", resource_id)

    toolkit.get_action("resource_validate")(
        {"ignore_auth": True},
        {"id": resource_id},
    )

    log.info("Finished background validation for resource %s", resource_id)
