from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, UnicodeText

from ckan.model.types import JsonDictType
from ckan.model.base import ActiveRecordMixin
from ckan.model import Session
from ckan.plugins import toolkit


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
