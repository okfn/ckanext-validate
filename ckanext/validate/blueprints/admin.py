import logging
from datetime import datetime, timezone

from flask import Blueprint

from ckan.lib import base
from ckan.plugins import toolkit

from ckanext.validate.model.validation import Validation
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


VALIDATION_STATISTICS_PERIODS = {
    "1_month": "1 month",
    "6_months": "6 months",
    "1_year": "1 year",
}


@validation_jobs_blueprint.route(
    "/ckan-admin/validation-statistics",
    methods=["GET"],
)
def validation_statistics():
    """Display validation statistics for a predefined reporting period."""
    context = {"user": toolkit.current_user.name}

    try:
        toolkit.check_access("sysadmin", context)
    except toolkit.NotAuthorized:
        base.abort(
            403,
            toolkit._("Need to be system administrator to administer"),
        )

    selected_period = toolkit.request.args.get(
        "period",
        "1_month",
    ).strip()

    if selected_period not in VALIDATION_STATISTICS_PERIODS:
        toolkit.h.flash_error(
            toolkit._("Invalid statistics period: {0}").format(
                selected_period
            )
        )
        selected_period = "1_month"

    report_end = datetime.now(timezone.utc)
    validations = Validation.get_by_period(
        selected_period,
        end_date=report_end,
    )
    summary = Validation.get_statistics_summary(validations)
    errors_by_type = Validation.group_errors_by_type(validations)
    resources = Validation.group_errors_by_resource(validations)
    timeline = Validation.get_statistics_timeline(
        validations,
        selected_period,
        end_date=report_end,
    )
    max_error_type_count = max(
        (item["count"] for item in errors_by_type),
        default=1,
    )
    max_timeline_error_count = max(
        (item["error_count"] for item in timeline),
        default=1,
    )

    resource_show = toolkit.get_action("resource_show")

    for resource_summary in resources:
        resource_summary["resource_name"] = resource_summary["resource_id"]
        resource_summary["resource_url"] = None

        try:
            resource = resource_show(
                context,
                {"id": resource_summary["resource_id"]},
            )
        except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
            continue

        resource_summary["resource_name"] = (
            resource.get("name")
            or resource.get("description")
            or resource_summary["resource_id"]
        )
        resource_summary["resource_url"] = toolkit.url_for(
            "resource.read",
            id=resource["package_id"],
            resource_id=resource["id"],
        )

    return base.render(
        "admin/validation_statistics.html",
        extra_vars={
            "summary": summary,
            "errors_by_type": errors_by_type,
            "resources": resources,
            "periods": VALIDATION_STATISTICS_PERIODS,
            "selected_period": selected_period,
            "timeline": timeline,
            "max_error_type_count": max_error_type_count,
            "max_timeline_error_count": max_timeline_error_count,
        },
    )
