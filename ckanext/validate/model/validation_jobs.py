from datetime import datetime, timezone
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
        return {cls.QUEUED, cls.STARTED, cls.DEFERRED, cls.SCHEDULED}

    @classmethod
    def running_statuses(cls):
        return {cls.RUNNING}

    @classmethod
    def error_statuses(cls):
        return {cls.FAILED, cls.STOPPED, cls.CANCELED, cls.ERROR}

    @classmethod
    def terminal_statuses(cls):
        return {
            cls.FINISHED,
            cls.FAILED,
            cls.STOPPED,
            cls.CANCELED,
            cls.ERROR,
        }


class ValidationJob(toolkit.BaseModel, ActiveRecordMixin):
    """Stores the status of each background validation job for a resource."""

    __tablename__ = "resource_validation_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(UnicodeText, nullable=False)
    status = Column(UnicodeText, nullable=False)
    create_timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
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
            status=status.value if isinstance(status, JobStatus) else status,
        )
        record.save()
        return record

    @classmethod
    def get(cls, job_id):
        return Session.query(cls).filter(cls.id == job_id).first()

    @classmethod
    def update(cls, resource_id, status):
        record = cls.get_latest_job_for_resource(resource_id)
        if not record:
            raise ValueError(f"No existing job found for resource_id {resource_id}")
        return cls.update_by_id(record.id, status)

    @classmethod
    def update_by_id(cls, job_id, status):
        record = cls.get(job_id)
        if not record:
            raise ValueError(f"No existing job found for job_id {job_id}")

        record.status = status.value if isinstance(status, JobStatus) else status
        if status in JobStatus.terminal_statuses():
            record.finish_timestamp = datetime.now(timezone.utc)

        record.commit()
        log.info(
            "ValidationJob id=%s for resource_id=%s updated to status=%s",
            record.id,
            record.resource_id,
            status,
        )
        return record

    @classmethod
    def get_all(cls, status=None, limit=100):
        query = Session.query(cls)

        if status:
            query = query.filter(cls.status == status)

        return (
            query
            .order_by(cls.create_timestamp.desc())
            .limit(limit)
            .all()
        )

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
        """Return the most recent validation job status for a resource, or None."""
        record = cls.get_latest_job_for_resource(resource_id)
        if record:
            return record.status
        return None

    def as_dict(self):
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "status": self.status,
            "created": self.create_timestamp.isoformat() if self.create_timestamp else None,
            "finished": self.finish_timestamp.isoformat() if self.finish_timestamp else None,
        }
