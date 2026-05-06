import logging

from flask import Blueprint

from ckan.lib import base
from ckan.plugins import toolkit

from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob

log = logging.getLogger(__name__)

validation_jobs_blueprint = Blueprint(
    "validate_admin", __name__,
)


@validation_jobs_blueprint.route("/ckan-admin/validation-jobs", methods=["GET"])
def validation_jobs():
    if not getattr(toolkit.current_user, "sysadmin", False):
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
    context = {"ignore_auth": True}

    def _enrich(job_dict):
        try:
            resource = resource_show(context, {"id": job_dict["resource_id"]})
            job_dict["resource_name"] = resource.get("name") or resource.get("description") or job_dict["resource_id"]
            job_dict["resource_url"] = toolkit.url_for(
                "resource.read",
                id=resource["package_id"],
                resource_id=job_dict["resource_id"],
            )
        except toolkit.ObjectNotFound:
            job_dict["resource_name"] = job_dict["resource_id"]
            job_dict["resource_url"] = None
        return job_dict

    return base.render(
        "admin/validation_jobs.html",
        extra_vars={
            "jobs": [_enrich(job.as_dict()) for job in jobs],
            "available_statuses": available_statuses,
            "selected_status": selected_status,
        },
    )
