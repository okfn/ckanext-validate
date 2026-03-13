import logging

from flask import Blueprint

from ckan.lib import base
from ckan.plugins import toolkit

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
        resource = toolkit.get_action("resource_show")(
            {}, {"id": resource_id}
        )
    except toolkit.ObjectNotFound:
        base.abort(404, toolkit._("Resource not found"))

    errors = {}
    if toolkit.request.method == "POST":
        try:
            context = {"user": toolkit.current_user.name}
            resource = toolkit.get_action("resource_validate")(
                context, {"id": resource_id}
            )
            toolkit.h.flash_success(toolkit._("Validation completed."))
        except toolkit.ValidationError as e:
            errors = e.error_dict
        except toolkit.NotAuthorized:
            base.abort(403, toolkit._("Not authorized to validate this resource"))

    return base.render(
        "package/resource_validate.html",
        extra_vars={
            "pkg_dict": pkg_dict,
            "res": resource,
            "errors": errors,
        },
    )
