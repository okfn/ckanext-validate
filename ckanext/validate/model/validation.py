import datetime

from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, UnicodeText

from ckan.model.base import ActiveRecordMixin
from ckan.model import Session
from ckan.plugins import toolkit


class Validation(toolkit.BaseModel, ActiveRecordMixin):
    """Stores the result of each Frictionless validation run for a resource."""

    __tablename__ = "resource_validation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(String(36), nullable=False, index=True)
    status = Column(UnicodeText, nullable=False)
    error_count = Column(Integer, nullable=False, default=0)
    errors = Column(JSON, nullable=False, default=list)
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

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

    def as_dict(self):
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "status": self.status,
            "error_count": self.error_count,
            "errors": self.errors if self.errors is not None else [],
            "created": self.created.isoformat() if self.created else None,
        }
