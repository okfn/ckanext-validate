import logging
import os
import tempfile

from flask import Blueprint
from frictionless import Resource, system

from ckan.lib import base
from ckan.plugins import toolkit

from ckanext.validate.model.validation import Validation

log = logging.getLogger(__name__)

resource_validate_blueprint = Blueprint(
    "resource_validate", __name__, url_prefix="/dataset"
)

validate_test_file_blueprint = Blueprint(
    "validate_test_file", __name__, url_prefix="/validate"
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
            resource = toolkit.get_action("resource_validate")(context, {"id": resource_id})
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


@validate_test_file_blueprint.route("/test-file", methods=["GET", "POST"])
def test_file():
    errors = []
    report_valid = None
    filename = None
    success = False

    if toolkit.request.method == "POST":
        uploaded_file = toolkit.request.files.get("file")

        if not uploaded_file or not uploaded_file.filename:
            toolkit.h.flash_error(toolkit._("Please select a CSV file to validate."))
            return base.render(
                "validate/test_file.html",
                extra_vars={"success": success},
            )

        filename = uploaded_file.filename
        if not filename.lower().endswith(".csv"):
            toolkit.h.flash_error(toolkit._("Only CSV files are supported."))
            return base.render(
                "validate/test_file.html",
                extra_vars={"success": success},
            )

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
        try:
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
            return base.render(
                "validate/test_file.html",
                extra_vars={"success": success},
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            os.close(tmp_fd)  # TODO: check!
            success = True

    return base.render(
        "validate/test_file.html",
        extra_vars={
            "errors": errors,
            "report_valid": report_valid,
            "filename": filename,
            "success": success,
        },
    )
