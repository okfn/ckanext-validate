import logging

from flask import Blueprint

from ckan.lib import base
from ckan.plugins import toolkit

from ckanext.validate.model.validation import Validation

log = logging.getLogger(__name__)

resource_validate_blueprint = Blueprint(
    "resource_validate", __name__, url_prefix="/dataset"
)


@resource_validate_blueprint.route(
    "/<package_id>/resource/<resource_id>/validate", methods=["GET", "POST"]
)
def validate(package_id, resource_id):
    try:
        pkg_dict = toolkit.get_action("package_show")(
            {}, {"id": package_id}
        )
    except toolkit.ObjectNotFound:
        base.abort(404, toolkit._("Package not found"))

    try:
        resource = toolkit.get_action("resource_show")(
            {}, {"id": resource_id}
        )
    except toolkit.ObjectNotFound:
        base.abort(404, toolkit._("Resource not found"))

    errors = {}
    if toolkit.request.method == "POST":
        log.info(
            "Manual validation request package_id=%s resource_id=%s current_user=%r method=%s",
            package_id,
            resource_id,
            getattr(toolkit.current_user, "name", None),
            toolkit.request.method,
        )
        try:
            context = {"user": toolkit.current_user.name}
            toolkit.get_action("resource_validate")(context, {"id": resource_id})
        except toolkit.ValidationError as e:
            errors = e.error_dict
        except toolkit.NotAuthorized:
            base.abort(403, toolkit._("Not authorized to validate this resource"))

        if not errors:
            record = Validation.get_latest(resource_id)
            if record and record.status == "success":
                toolkit.h.flash_success(toolkit._("Validation completed. No errors found."))
            elif record and record.status == "failure":
                msg = toolkit._("Validation completed. {} errors found.").format(record.error_count)
                toolkit.h.flash_error(msg)
            else:
                toolkit.h.flash_success(toolkit._("Validation completed."))

    record = Validation.get_latest(resource_id)
    validation_errors = record.errors if record else []

    return base.render(
        "package/resource_validate.html",
        extra_vars={
            "pkg_dict": pkg_dict,
            "package": pkg_dict,
            "pkg": pkg_dict,
            "resource": resource,
            "res": resource,
            "errors": errors,
            "validation_errors": validation_errors or [],
            "validation_error_count": record.error_count if record else 0,
        },
    )
