import json
import logging
import os
import tempfile

from flask import Blueprint
from frictionless import Resource, system

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
            resource = toolkit.get_action("resource_validate")(
                context, {"id": resource_id}
            )

            status = resource.get("validation_status")
            error_count = resource.get("validation_error_count", 0)
            if status == "success":
                toolkit.h.flash_success(toolkit._("Validation completed. No errors found."))
            elif status == "failure":
                msg = toolkit._("Validation completed. {} errors found.").format(error_count)
                toolkit.h.flash_error(msg)
            else:
                toolkit.h.flash_success(toolkit._("Validation completed."))

        except toolkit.ValidationError as e:
            errors = e.error_dict
        except toolkit.NotAuthorized:
            base.abort(403, toolkit._("Not authorized to validate this resource"))

    validation_errors = []
    raw = resource.get("validation_errors")
    if raw:
        try:
            validation_errors = json.loads(raw)
        except (ValueError, TypeError):
            pass

    return base.render(
        "package/resource_validate.html",
        extra_vars={
            "pkg_dict": pkg_dict,
            "package": pkg_dict,
            "pkg": pkg_dict,
            "resource": resource,
            "res": resource,
            "errors": errors,
            "validation_errors": validation_errors,
        },
    )


validate_test_file_blueprint = Blueprint(
    "validate_test_file", __name__
)


@validate_test_file_blueprint.route("/validate/test-file", methods=["GET", "POST"])
def test_file():
    errors = []
    report_valid = None
    filename = None

    if toolkit.request.method == "POST":
        uploaded_file = toolkit.request.files.get("file")

        if not uploaded_file or not uploaded_file.filename:
            toolkit.h.flash_error(toolkit._("Please select a CSV file to validate."))
        else:
            filename = uploaded_file.filename
            if not filename.lower().endswith(".csv"):
                toolkit.h.flash_error(toolkit._("Only CSV files are supported."))
            else:
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
                try:
                    os.close(tmp_fd)
                    uploaded_file.save(tmp_path)

                    with system.use_context(trusted=True):
                        res = Resource("file://" + tmp_path, format="csv")
                        report = res.validate()

                    report_valid = report.valid

                    for task in report.tasks:
                        for err in task.errors:
                            errors.append({
                                "row": getattr(err, "row_number", None),
                                "field": getattr(err, "field_name", None),
                                "message": err.message,
                            })

                    if not report.valid and not errors:
                        errors.append({
                            "message": toolkit._("Structural validation error"),
                        })

                except Exception as exc:
                    log.exception("Error validating uploaded file")
                    toolkit.h.flash_error(
                        toolkit._("System error during validation: {0}").format(str(exc))
                    )
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

    return base.render(
        "validate/test_file.html",
        extra_vars={
            "errors": errors,
            "report_valid": report_valid,
            "filename": filename,
        },
    )
