from datetime import datetime

from collections import OrderedDict

import ckan.plugins.toolkit as toolkit

from ckanext.validate.model.validation import Validation
from ckanext.validate.model.validation_jobs import JobStatus, ValidationJob


MAX_ERROR_ROWS_PER_GROUP = 20


def collect_report_errors(report):
    descriptor = report.to_descriptor() or {}
    errors = []

    for task in descriptor.get("tasks", []):
        task_labels = list(task.get("labels") or [])

        for error in task.get("errors", []):
            enriched_error = dict(error)
            if task_labels and not enriched_error.get("labels"):
                enriched_error["labels"] = task_labels
            errors.append(enriched_error)

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

    return {
        "type": error.get("type"),
        "title": (
            error.get("title")
            or error.get("type")
            or error.get("message")
            or toolkit._("Validation error")
        ),
        "description": error.get("description"),
        "message": error.get("message") or toolkit._("Unknown validation error"),
        "row_number": row_number,
        "row_numbers": row_numbers,
        "field_name": error.get("fieldName") or error.get("field"),
        "field_number": error.get("fieldNumber"),
        "cells": list(error.get("cells") or []),
        "labels": list(error.get("labels") or []),
    }


def _header_cells_from_items(items):
    for item in items:
        if item["labels"]:
            return list(item["labels"])
    return []


def _preview_for_blank_label(items):
    header_cells = _header_cells_from_items(items)
    if not header_cells:
        return None

    highlight_columns = sorted(
        {
            item["field_number"]
            for item in items
            if item.get("field_number")
        }
    )

    total_columns = max(len(header_cells), max(highlight_columns or [0]), 1)

    cells = []
    for index in range(total_columns):
        if index < len(header_cells):
            cells.append(header_cells[index] or "")
        else:
            cells.append("")

    return {
        "column_numbers": list(range(1, total_columns + 1)),
        "rows": [
            {
                "row_number": 1,
                "cells": cells,
                "highlight_columns": highlight_columns,
            }
        ],
    }


def _preview_for_blank_row(items):
    max_columns = max(
        6,
        max((len(item["labels"]) for item in items), default=0),
        max((len(item["cells"]) for item in items), default=0),
    )

    rows = []
    for item in items:
        rows.append(
            {
                "row_number": item["row_number"],
                "cells": [""] * max_columns,
                "highlight_columns": list(range(1, max_columns + 1)),
            }
        )

    return {
        "column_numbers": list(range(1, max_columns + 1)),
        "rows": rows,
    }


def _preview_for_general_rows(items):
    max_columns = max(
        1,
        max((len(item["labels"]) for item in items), default=0),
        max((len(item["cells"]) for item in items), default=0),
        max((item["field_number"] or 0 for item in items), default=0),
    )

    rows = []
    for item in items:
        cells = []
        raw_cells = item["cells"]

        for index in range(max_columns):
            if index < len(raw_cells):
                cells.append(raw_cells[index] or "")
            else:
                cells.append("")

        highlight_columns = []
        if item["field_number"]:
            highlight_columns = [item["field_number"]]

        rows.append(
            {
                "row_number": item["row_number"],
                "cells": cells,
                "highlight_columns": highlight_columns,
            }
        )

    return {
        "column_numbers": list(range(1, max_columns + 1)),
        "rows": rows,
    }


def _build_error_preview(group):
    items = group["items"]
    if not items:
        return None

    error_type = group.get("type")

    if error_type == "blank-label":
        return _preview_for_blank_label(items)

    if error_type == "blank-row":
        return _preview_for_blank_row(items)

    return _preview_for_general_rows(items)


def group_validation_errors(errors, limit=MAX_ERROR_ROWS_PER_GROUP):
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
        group["preview"] = _build_error_preview(group)
        result.append(group)

    return result


def get_resource_validation_job_status(resource_dict):
    if not resource_dict:
        return None

    resource_id = resource_dict.get("id")
    if not resource_id:
        return None

    return ValidationJob.get_latest_job_status_for_resource(resource_id)


def get_resource_validation_state(resource_dict):
    if not resource_dict:
        return None

    status = Validation.get_resource_status(resource_dict.get("id"))
    if status:
        return status

    job_status = get_resource_validation_job_status(resource_dict)
    if job_status in JobStatus.pending_statuses():
        return "pending"

    if job_status in JobStatus.running_statuses():
        return "running"

    if job_status in JobStatus.error_statuses():
        return "error"

    return None


def format_timestamp_for_display(value):
    if not value:
        return None

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value

    return value.strftime("%Y-%m-%d %H:%M:%S")


def normalize_format(resource_dict):
    """Return the resource format in lowercase, or empty string."""
    return (resource_dict.get("format") or "").strip().lower()
