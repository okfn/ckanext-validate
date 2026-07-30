from collections import Counter
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from sqlalchemy import Column, DateTime, Index, Integer, UnicodeText

from ckan.model.types import JsonDictType
from ckan.model.base import ActiveRecordMixin
from ckan.model import Session
from ckan.plugins import toolkit


VALIDATION_PERIODS = {
    "1_month": 1,
    "6_months": 6,
    "1_year": 12,
}


class Validation(toolkit.BaseModel, ActiveRecordMixin):
    """Stores the result of each Frictionless validation run for a resource."""

    __tablename__ = "resource_validation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(UnicodeText, nullable=False)
    status = Column(UnicodeText, nullable=False)
    error_count = Column(Integer, nullable=False, default=0)
    errors = Column(JsonDictType)
    created = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_resource_validation_resource_id_created", "resource_id", "created"),
    )

    def __repr__(self):
        return (
            f"<Validation resource_id={self.resource_id!r} "
            f"status={self.status!r} errors={self.error_count}>"
        )

    @classmethod
    def create(cls, resource_id, status, error_count, errors):
        record = cls(
            resource_id=resource_id,
            status=status,
            error_count=error_count,
            errors=errors,
        )
        record.save()
        return record

    @classmethod
    def get_latest(cls, resource_id):
        return (
            Session.query(cls)
            .filter(cls.resource_id == resource_id)
            .order_by(cls.created.desc())
            .first()
        )

    @classmethod
    def get_by_date_range(cls, start_date, end_date):
        """Return validations created within a date range.

        ``start_date`` is inclusive and ``end_date`` is exclusive. This avoids
        returning the same validation in two consecutive reporting periods.
        """
        if (
            not isinstance(start_date, datetime)
            or not isinstance(end_date, datetime)
        ):
            raise ValueError("start_date and end_date must be datetime objects")

        if start_date >= end_date:
            raise ValueError("start_date must be earlier than end_date")

        return (
            Session.query(cls)
            .filter(
                cls.created >= start_date,
                cls.created < end_date,
            )
            .order_by(cls.created.desc())
            .all()
        )

    @classmethod
    def get_by_period(cls, period, end_date=None):
        """Return validations from one of the supported reporting periods."""
        months = VALIDATION_PERIODS.get(period)
        if months is None:
            raise ValueError(
                "Invalid period. Valid values are: {0}".format(
                    ", ".join(VALIDATION_PERIODS)
                )
            )

        end_date = end_date or datetime.now(timezone.utc)
        if not isinstance(end_date, datetime):
            raise ValueError("end_date must be a datetime object")

        start_date = end_date - relativedelta(months=months)
        return cls.get_by_date_range(start_date, end_date)

    @staticmethod
    def _get_error_type(error):
        """Return a stable grouping key for a stored validation error."""
        if not isinstance(error, dict):
            return "unknown"

        return (
            error.get("type")
            or error.get("title")
            or error.get("message")
            or "unknown"
        )

    @classmethod
    def group_errors_by_type(cls, validations):
        """Count stored errors by error type for the given validations."""
        error_counts = Counter()

        for validation in validations:
            errors = (
                validation.errors
                if isinstance(validation.errors, list)
                else []
            )

            for error in errors:
                error_counts[cls._get_error_type(error)] += 1

            missing_details = max(
                (validation.error_count or 0) - len(errors),
                0,
            )
            if missing_details:
                error_counts["unknown"] += missing_details

        return [
            {"type": error_type, "count": count}
            for error_type, count in sorted(
                error_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    @classmethod
    def group_errors_by_resource(cls, validations):
        """Summarize validations and errors for each resource."""
        resources = {}

        for validation in validations:
            summary = resources.setdefault(
                validation.resource_id,
                {
                    "resource_id": validation.resource_id,
                    "validation_count": 0,
                    "valid_count": 0,
                    "invalid_count": 0,
                    "error_count": 0,
                    "errors_by_type": Counter(),
                },
            )

            summary["validation_count"] += 1
            summary["error_count"] += validation.error_count or 0

            if validation.status == "success":
                summary["valid_count"] += 1
            elif validation.status == "failure":
                summary["invalid_count"] += 1

            errors = (
                validation.errors
                if isinstance(validation.errors, list)
                else []
            )

            for error in errors:
                error_type = cls._get_error_type(error)
                summary["errors_by_type"][error_type] += 1

            missing_details = max(
                (validation.error_count or 0) - len(errors),
                0,
            )
            if missing_details:
                summary["errors_by_type"]["unknown"] += missing_details

        result = []

        for summary in resources.values():
            summary["errors_by_type"] = [
                {"type": error_type, "count": count}
                for error_type, count in sorted(
                    summary["errors_by_type"].items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ]
            result.append(summary)

        return sorted(
            result,
            key=lambda item: (
                -item["error_count"],
                item["resource_id"],
            ),
        )

    @classmethod
    def get_resource_status(cls, resource_id):
        """Return the most recent validation status for a resource, or None."""
        record = cls.get_latest(resource_id)
        if record:
            return record.status
        return None

    def as_dict(self):
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "status": self.status,
            "error_count": self.error_count,
            "errors": self.errors if self.errors is not None else [],
            "created": self.created.isoformat() if self.created else None,
        }
