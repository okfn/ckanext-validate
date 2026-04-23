import logging

import ckan.plugins.toolkit as toolkit

from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob

log = logging.getLogger(__name__)


"""
To process the background jobs queue, use the following command:

ckan -c /etc/ckan/default/ckan.ini jobs worker

https://docs.ckan.org/en/2.11/maintaining/cli.html
"""


def run_resource_validation_job(resource_id, job_id=None):
    """
    Execute validation in the background job and ensure the resource
    is updated with a final result, including the error case.
    """
    log.info("Starting background validation for resource %s", resource_id)

    site_user = toolkit.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"ignore_auth": True, "user": site_user["name"]}

    current_job = ValidationJob.get_latest_job_for_resource(resource_id)
    # si el job existe finalizarlos/cancelarlos/terminarlos

    if current_job and current_job.status in JobStatus.pending_statuses():
        log.debug(
            "Existing pending job found for resource %s (status=%s), marking as stopped",
            resource_id,
            current_job.status,
        )
        ValidationJob.update(resource_id=resource_id, status=JobStatus.STOPPED)
 
    try:
        ValidationJob.update(resource_id=resource_id, status=JobStatus.RUNNING)
    except ValueError:
        # Fallback por si el registro no existiera por datos viejos o ejecución manual
        ValidationJob.create(resource_id=resource_id, status=JobStatus.RUNNING)

    try:
        toolkit.get_action("resource_validate")(
            context,
            {"id": resource_id},
        )
        log.info("Finished background validation for resource %s", resource_id)
        # TODO: Mejorar esto para actualizar el job específico en vez de asumir que el último es el correcto
        ValidationJob.update(resource_id=resource_id, status=JobStatus.FINISHED)

    except Exception:
        log.exception(
            "Background validation failed for resource %s",
            resource_id,
        )
        try:
            ValidationJob.update(resource_id=resource_id, status=JobStatus.ERROR)
        # TODO: Mejorar esto para actualizar el job específico en vez de asumir que el último es el correcto
        except ValueError:
            ValidationJob.create(resource_id=resource_id, status=JobStatus.ERROR)
