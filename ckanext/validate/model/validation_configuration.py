from copy import deepcopy
from datetime import datetime, timezone
from sqlalchemy import Integer
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    UnicodeText,
    UniqueConstraint,
)

from ckan.model import Session
from ckan.model.base import ActiveRecordMixin
from ckan.model.types import JsonDictType
from ckan.plugins import toolkit

from ckanext.validate.validation_schema import (
    normalize_schema_descriptor,
    schema_from_descriptor,
)


class ValidationConfiguration(
    toolkit.BaseModel,
    ActiveRecordMixin,
):
    """Reusable Frictionless validation configuration for CSV resources."""

    __tablename__ = "validate_validation_configuration"

    id = Column(
        UnicodeText,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name = Column(
        UnicodeText,
        nullable=False,
        unique=True,
    )

    description = Column(
        UnicodeText,
        nullable=True,
    )

    schema_descriptor = Column(
        JsonDictType,
        nullable=False,
    )

    active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    create_timestamp = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    update_timestamp = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index(
            "ix_validate_validation_configuration_active_name",
            "active",
            "name",
        ),
    )

    def __repr__(self):
        return (
            "<ValidationConfiguration "
            f"id={self.id!r} "
            f"name={self.name!r} "
            f"active={self.active!r}>"
        )

    @classmethod
    def create(
        cls,
        name,
        schema_descriptor,
        description=None,
        active=True,
    ):
        """Create a configuration after validating its Frictionless schema."""
        normalized_descriptor = normalize_schema_descriptor(
            schema_descriptor
        )

        record = cls(
            name=name,
            description=description,
            schema_descriptor=normalized_descriptor,
            active=active,
        )

        record.save()
        return record

    @classmethod
    def get(cls, configuration_id):
        """Return a configuration by ID."""
        return (
            Session.query(cls)
            .filter(cls.id == configuration_id)
            .first()
        )

    @classmethod
    def get_active(cls, configuration_id):
        """Return an active configuration by ID."""
        return (
            Session.query(cls)
            .filter(
                cls.id == configuration_id,
                cls.active.is_(True),
            )
            .first()
        )

    @classmethod
    def get_by_name(cls, name):
        """Return a configuration by name."""
        return (
            Session.query(cls)
            .filter(cls.name == name)
            .first()
        )

    @classmethod
    def get_all(cls, active=None):
        """List configurations ordered by name."""
        query = Session.query(cls)

        if active is not None:
            query = query.filter(cls.active.is_(active))

        return query.order_by(cls.name.asc()).all()

    def update_values(self, **values):
        """Update allowed fields and revalidate the schema when necessary."""
        allowed_fields = {
            "name",
            "description",
            "schema_descriptor",
            "active",
        }

        unknown_fields = set(values) - allowed_fields

        if unknown_fields:
            raise ValueError(
                "Unknown validation configuration fields: {0}".format(
                    ", ".join(sorted(unknown_fields))
                )
            )

        if "schema_descriptor" in values:
            values["schema_descriptor"] = (
                normalize_schema_descriptor(
                    values["schema_descriptor"]
                )
            )

        for key, value in values.items():
            setattr(self, key, value)

        self.commit()

        return self

    def delete(self):
        """Delete this configuration instance."""
        Session.delete(self)
        Session.commit()

    @classmethod
    def delete_by_id(cls, configuration_id):
        """Delete a configuration and return whether it existed."""
        record = cls.get(configuration_id)

        if not record:
            return False

        record.delete()

        return True

    def get_schema(self):
        """Return this configuration as a Frictionless Schema object."""
        return schema_from_descriptor(
            self.schema_descriptor
        )

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schema": deepcopy(
                self.schema_descriptor or {}
            ),
            "active": self.active,
            "created": (
                self.create_timestamp.isoformat()
                if self.create_timestamp
                else None
            ),
            "updated": (
                self.update_timestamp.isoformat()
                if self.update_timestamp
                else None
            ),
        }


class ValidationConfigurationAssignment(
    toolkit.BaseModel,
    ActiveRecordMixin,
):
    """Assign a validation configuration to a CKAN target."""

    __tablename__ = (
        "validate_validation_configuration_assignment"
    )

    TARGET_RESOURCE = "resource"
    TARGET_PACKAGE = "package"
    TARGET_GLOBAL = "global"

    VALID_TARGET_TYPES = {
        TARGET_RESOURCE,
        TARGET_PACKAGE,
        TARGET_GLOBAL,
    }

    GLOBAL_TARGET_ID = "global"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    configuration_id = Column(
        UnicodeText,
        nullable=False,
    )

    target_type = Column(
        UnicodeText,
        nullable=False,
    )

    target_id = Column(
        UnicodeText,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "target_type",
            "target_id",
            name="uq_validation_configuration_target",
        ),
        Index(
            "ix_validation_configuration_assignment_configuration",
            "configuration_id",
        ),
    )

    @classmethod
    def get_for_target(
        cls,
        target_type,
        target_id,
    ):
        return (
            Session.query(cls)
            .filter(
                cls.target_type == target_type,
                cls.target_id == target_id,
            )
            .first()
        )

    @classmethod
    def get_for_resource(cls, resource_id):
        return cls.get_for_target(
            cls.TARGET_RESOURCE,
            resource_id,
        )

    @classmethod
    def get_for_package(cls, package_id):
        return cls.get_for_target(
            cls.TARGET_PACKAGE,
            package_id,
        )

    @classmethod
    def get_global(cls):
        return cls.get_for_target(
            cls.TARGET_GLOBAL,
            cls.GLOBAL_TARGET_ID,
        )

    @classmethod
    def assign(
        cls,
        configuration_id,
        target_type,
        target_id=None,
    ):
        if target_type not in cls.VALID_TARGET_TYPES:
            raise ValueError(
                "Invalid validation configuration target type: "
                f"{target_type}"
            )

        configuration = ValidationConfiguration.get_active(
            configuration_id
        )

        if configuration is None:
            raise ValueError(
                "The validation configuration does not exist "
                "or is inactive."
            )

        if target_type == cls.TARGET_GLOBAL:
            target_id = cls.GLOBAL_TARGET_ID

        if not target_id:
            raise ValueError(
                "A target ID is required."
            )

        assignment = cls.get_for_target(
            target_type,
            target_id,
        )

        if assignment:
            assignment.configuration_id = configuration_id
            assignment.commit()
            return assignment

        assignment = cls(
            configuration_id=configuration_id,
            target_type=target_type,
            target_id=target_id,
        )

        assignment.save()
        return assignment

    @classmethod
    def assign_to_resource(
        cls,
        resource_id,
        configuration_id,
    ):
        return cls.assign(
            configuration_id=configuration_id,
            target_type=cls.TARGET_RESOURCE,
            target_id=resource_id,
        )

    @classmethod
    def assign_to_package(
        cls,
        package_id,
        configuration_id,
    ):
        return cls.assign(
            configuration_id=configuration_id,
            target_type=cls.TARGET_PACKAGE,
            target_id=package_id,
        )

    @classmethod
    def assign_global(cls, configuration_id):
        return cls.assign(
            configuration_id=configuration_id,
            target_type=cls.TARGET_GLOBAL,
        )

    @classmethod
    def delete_for_target(
        cls,
        target_type,
        target_id,
    ):
        assignment = cls.get_for_target(
            target_type,
            target_id,
        )

        if assignment is None:
            return False

        Session.delete(assignment)
        Session.commit()

        return True