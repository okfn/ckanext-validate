import datetime
import enum
import logging

from sqlalchemy import Column, DateTime, Index, Integer, UnicodeText

from ckan.model.base import ActiveRecordMixin
from ckan.model import Session
from ckan.plugins import toolkit


log = logging.getLogger(__name__)


class JobStatus(str, enum.Enum):
    # Pending / in-flight
    QUEUED = "queued"
    STARTED = "started"
    DEFERRED = "deferred"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    # Terminal — success
    FINISHED = "finished"
    # Terminal — failure
    FAILED = "failed"
    STOPPED = "stopped"
    CANCELED = "canceled"
    ERROR = "error"

    @classmethod
    def pending_statuses(cls):
        return {cls.QUEUED, cls.STARTED, cls.DEFERRED, cls.SCHEDULED, cls.RUNNING}

    @classmethod
    def error_statuses(cls):
        return {cls.FAILED, cls.STOPPED, cls.CANCELED}


class ValidationJob(toolkit.BaseModel, ActiveRecordMixin):
    """Stores the result of each Frictionless validation run for a resource."""

    __tablename__ = "resource_validation_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(UnicodeText, nullable=False)
    status = Column(UnicodeText, nullable=False)
    create_timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    finish_timestamp = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_resource_validation_jobs_resource_id_create_timestamp", "resource_id", "create_timestamp"),
    )

    def __repr__(self):
        return (
            f"<ValidationJob resource_id={self.resource_id!r} "
            f"status={self.status!r}>"
        )

    @classmethod
    def create(cls, resource_id, status):
        record = cls(
            resource_id=resource_id,
            status=status,
        )
        record.save()
        return record

    @classmethod
    def update(cls, resource_id, status):
        record = cls.get_latest_job_for_resource(resource_id)
        if record:
            record.status = status
            if status in (JobStatus.FINISHED, JobStatus.ERROR):
                record.finish_timestamp = datetime.datetime.utcnow()
            log.debug("Updating ValidationJob for resource_id %s to status %s", resource_id, status)
            record.commit()
            log.info("ValidationJob for resource_id %s updated to status %s", resource_id, status)
            log.info("ValidationJob record after update: %s", record)
            return record
        else:
            raise ValueError(f"No existing job found for resource_id {resource_id}")

    @classmethod
    def get_latest_job_for_resource(cls, resource_id):
        return (
            Session.query(cls)
            .filter(cls.resource_id == resource_id)
            .order_by(cls.create_timestamp.desc())
            .first()
        )

    @classmethod
    def get_latest_job_status_for_resource(cls, resource_id):
        record = cls.get_latest_job_for_resource(resource_id)
        if record:
            return record.status
        else:
            return None

    def as_dict(self):
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "status": self.status,
            "created": self.create_timestamp.isoformat() if self.create_timestamp else None,
            "finished": self.finish_timestamp.isoformat() if self.finish_timestamp else None,
        }
