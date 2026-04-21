import logging
import os
import tempfile
from collections import OrderedDict

from flask import Blueprint
from frictionless import Resource, system

from ckan.lib import base
from ckan.plugins import toolkit

from ckanext.validate.model.validation import Validation

log = logging.getLogger(__name__)

MAX_ERROR_ROWS_PER_GROUP = 20

resource_validate_blueprint = Blueprint(
    "resource_validate", __name__, url_prefix="/dataset"
)

validate_test_file_blueprint = Blueprint(
    "validate_test_file", __name__, url_prefix="/validate"
)


def _collect_report_errors(report):
    descriptor = report.to_descriptor() or {}
    errors = []

    for task in descriptor.get("tasks", []):
        errors.extend(task.get("errors", []))

    if not report.valid and not errors:
        errors.append(
            {
                "type": "structure-error",
                "title": toolkit._("Structural validation error"),
                "description": toolkit._(
                    "The validator could not extract row-level errors from the report."
                ),
                "message": toolkit._("Structural validation error"),
                "rowNumber": None,
                "rowNumbers": [],
                "fieldName": None,
                "fieldNumber": None,
                "cells": [],
                "labels": [],
            }
        )

    return errors


def _normalize_error(error):
    row_numbers = list(error.get("rowNumbers") or [])
    row_number = error.get("rowNumber", error.get("row"))

    if row_number is not None and row_number not in row_numbers:
        row_numbers.insert(0, row_number)

    title = (
        error.get("title")
        or error.get("type")
        or error.get("message")
        or toolkit._("Validation error")
    )

    return {
        "type": error.get("type"),
        "title": title,
        "description": error.get("description"),
        "message": error.get("message") or toolkit._("Unknown validation error"),
        "row_number": row_number,
        "row_numbers": row_numbers,
        "field_name": error.get("fieldName") or error.get("field"),
        "field_number": error.get("fieldNumber"),
        "cells": list(error.get("cells") or []),
        "labels": list(error.get("labels") or []),
    }


def _build_error_preview(items):
    if not items:
        return None

    header_items = [item for item in items if item["labels"]]
    if header_items:
        base_item = header_items[0]
        max_columns = max(
            len(base_item["labels"]),
            max((item["field_number"] or 0) for item in header_items),
            1,
        )

        return {
            "column_numbers": list(range(1, max_columns + 1)),
            "rows": [
                {
                    "row_number": 1,
                    "cells": [
                        base_item["labels"][index]
                        if index < len(base_item["labels"])
                        else ""
                        for index in range(max_columns)
                    ],
                    "highlight_columns": [
                        item["field_number"]
                        for item in header_items
                        if item["field_number"]
                    ],
                }
            ],
        }

    max_columns = max(
        max((len(item["cells"]) for item in items), default=0),
        max((item["field_number"] or 0 for item in items), default=0),
        1,
    )

    rows = []
    for item in items:
        if item["field_number"]:
            highlight_columns = [item["field_number"]]
        elif item["type"] == "blank-row":
            highlight_columns = list(range(1, max_columns + 1))
        else:
            highlight_columns = []

        rows.append(
            {
                "row_number": item["row_number"],
                "cells": [
                    item["cells"][index] if index < len(item["cells"]) else ""
                    for index in range(max_columns)
                ],
                "highlight_columns": highlight_columns,
            }
        )

    return {
        "column_numbers": list(range(1, max_columns + 1)),
        "rows": rows,
    }


def _group_validation_errors(errors, limit=MAX_ERROR_ROWS_PER_GROUP):
    groups = OrderedDict()

    for raw_error in errors or []:
        item = _normalize_error(raw_error)
        key = item["type"] or item["title"] or item["message"]

        if key not in groups:
            groups[key] = {
                "key": key,
                "type": item["type"],
                "title": item["title"],
                "description": item["description"],
                "count": 0,
                "items": [],
            }

        groups[key]["count"] += 1
        if len(groups[key]["items"]) < limit:
            groups[key]["items"].append(item)

    result = []
    for group in groups.values():
        group["truncated"] = group["count"] > limit
        group["preview"] = _build_error_preview(group["items"])
        result.append(group)

    return result


@resource_validate_blueprint.route(
    "/<package_id>/resource/<resource_id>/validate", methods=["GET", "POST"]
)
def validate(package_id, resource_id):
    try:
        pkg_dict = toolkit.get_action("package_show")({}, {"id": package_id})
    except toolkit.ObjectNotFound:
        base.abort(404, toolkit._("Package not found"))

    try:
        resource = toolkit.get_action("resource_show")({}, {"id": resource_id})
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
                toolkit.h.flash_success(
                    toolkit._("Validation completed. No errors found.")
                )
            elif record and record.status == "failure":
                msg = toolkit._("Validation completed. {} errors found.").format(
                    record.error_count
                )
                toolkit.h.flash_error(msg)
            else:
                toolkit.h.flash_success(toolkit._("Validation completed."))

    record = Validation.get_latest(resource_id)
    validation_errors = record.errors if record else []
    validation_error_count = record.error_count if record else 0
    validation_error_groups = _group_validation_errors(validation_errors)

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
            "validation_error_count": validation_error_count,
            "validation_error_groups": validation_error_groups,
            "error_row_limit": MAX_ERROR_ROWS_PER_GROUP,
        },
    )


validate_test_file_blueprint = Blueprint("validate_test_file", __name__)


@validate_test_file_blueprint.route("/validate/test-file", methods=["GET", "POST"])
def test_file():
    errors = []
    error_groups = []
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
            errors = _collect_report_errors(report)
            error_groups = _group_validation_errors(errors)

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
            os.close(tmp_fd)
            success = True

    return base.render(
        "validate/test_file.html",
        extra_vars={
            "errors": errors,
            "error_groups": error_groups,
            "error_row_limit": MAX_ERROR_ROWS_PER_GROUP,
            "report_valid": report_valid,
            "filename": filename,
            "success": success,
        },
    )