import logging

from flask import Blueprint

from ckan.lib import base
from ckan.plugins import toolkit

from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob
from ckanext.validate.helpers import format_timestamp_for_display

log = logging.getLogger(__name__)

validation_jobs_blueprint = Blueprint(
    "validate_admin", __name__,
)


@validation_jobs_blueprint.route("/ckan-admin/validation-jobs", methods=["GET"])
def validation_jobs():
    context = {"user": toolkit.current_user.name}

    try:
        toolkit.check_access("sysadmin", context)
    except toolkit.NotAuthorized:
        base.abort(403, toolkit._("Need to be system administrator to administer"))

    available_statuses = [status.value for status in JobStatus]
    selected_status = toolkit.request.args.get("status", "").strip()

    if selected_status and selected_status not in available_statuses:
        toolkit.h.flash_error(
            toolkit._("Invalid job status: {0}").format(selected_status)
        )
        selected_status = ""

    jobs = ValidationJob.get_all(
        status=selected_status or None,
        limit=100,
    )

    resource_show = toolkit.get_action("resource_show")

    def _enrich(job_dict):
        context = {"user": toolkit.current_user.name}

        job_dict["created"] = format_timestamp_for_display(job_dict.get("created"))
        job_dict["finished"] = format_timestamp_for_display(job_dict.get("finished"))

        try:
            resource = resource_show(context, {"id": job_dict["resource_id"]})
            job_dict["resource_name"] = (
                resource.get("name")
                or resource.get("description")
                or job_dict["resource_id"]
            )
            job_dict["resource_url"] = toolkit.url_for(
                "resource.read",
                id=resource["package_id"],
                resource_id=job_dict["resource_id"],
            )
            return job_dict

        except toolkit.ObjectNotFound:
            deleted = ValidationJob.delete_for_resource(job_dict["resource_id"])
            log.info(
                "Removed %s orphan validation jobs for deleted resource %s",
                deleted,
                job_dict["resource_id"],
            )
            return None

    enriched_jobs = []

    for job in jobs:
        enriched_job = _enrich(job.as_dict())
        if enriched_job:
            enriched_jobs.append(enriched_job)

    return base.render(
        "admin/validation_jobs.html",
        extra_vars={
            "jobs": enriched_jobs,
            "available_statuses": available_statuses,
            "selected_status": selected_status,
        },
    )
