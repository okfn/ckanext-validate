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

    return base.render(
        "admin/validation_jobs.html",
        extra_vars={
            "jobs": [job.as_dict() for job in jobs],
            "available_statuses": available_statuses,
            "selected_status": selected_status,
        },
    )
