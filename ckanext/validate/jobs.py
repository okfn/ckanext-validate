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
    log.info(
        "Starting background validation for resource %s (job_id=%s)",
        resource_id,
        job_id,
    )

    site_user = toolkit.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"ignore_auth": True, "user": site_user["name"]}

    if job_id is not None:
        try:
            ValidationJob.update_by_id(job_id, JobStatus.RUNNING)
        except ValueError:
            # Fallback por si el registro no existiera por datos viejos o ejecución manual
            current_job = ValidationJob.create(
                resource_id=resource_id,
                status=JobStatus.RUNNING,
            )
            job_id = current_job.id
    else:
        current_job = ValidationJob.create(
            resource_id=resource_id,
            status=JobStatus.RUNNING,
        )
        job_id = current_job.id

    try:
        toolkit.get_action("resource_validate")(
            context,
            {"id": resource_id},
        )
        log.info(
            "Finished background validation for resource %s (job_id=%s)",
            resource_id,
            job_id,
        )
        ValidationJob.update_by_id(job_id, JobStatus.FINISHED)

    except Exception:
        log.exception(
            "Background validation failed for resource %s (job_id=%s)",
            resource_id,
            job_id,
        )
        try:
            ValidationJob.update_by_id(job_id, JobStatus.ERROR)
        except ValueError:
            ValidationJob.create(resource_id=resource_id, status=JobStatus.ERROR)
