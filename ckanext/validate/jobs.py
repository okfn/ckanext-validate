import logging

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
    Step 3 only:
    background job entrypoint for resource validation.

    The actual validation call will be added in step 4.
    """
    log.info(
        "Validation job dequeued for resource %s",
        resource_id,
    )
