import json

from sqlalchemy.exc import IntegrityError

from ckan.model import Session
from ckan.plugins import toolkit

from ckanext.validate.model.validation_configuration import (
    ValidationConfiguration,
)


def _get_configuration(configuration_id):
    configuration = ValidationConfiguration.get(configuration_id)

    if configuration is None:
        raise toolkit.ObjectNotFound(
            toolkit._(
                "Validation configuration {0} was not found."
            ).format(configuration_id)
        )

    return configuration


def _get_name(data_dict, required=True):
    if "name" not in data_dict:
        if required:
            raise toolkit.ValidationError(
                {
                    "name": [
                        toolkit._(
                            "A configuration name is required."
                        )
                    ]
                }
            )

        return None

    name = str(data_dict.get("name") or "").strip()

    if not name:
        raise toolkit.ValidationError(
            {
                "name": [
                    toolkit._(
                        "A configuration name is required."
                    )
                ]
            }
        )

    return name


def _get_description(data_dict):
    description = data_dict.get("description")

    if description is None:
        return None

    description = str(description).strip()
    return description or None


def _get_schema_descriptor(data_dict, required=True):
    """Return the schema descriptor from a dictionary or JSON string."""
    has_schema = "schema" in data_dict
    has_schema_descriptor = "schema_descriptor" in data_dict

    if not has_schema and not has_schema_descriptor:
        if required:
            raise toolkit.ValidationError(
                {
                    "schema": [
                        toolkit._(
                            "A Frictionless schema is required."
                        )
                    ]
                }
            )

        return None

    value = (
        data_dict.get("schema")
        if has_schema
        else data_dict.get("schema_descriptor")
    )

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise toolkit.ValidationError(
                {
                    "schema": [
                        toolkit._(
                            "The schema is not valid JSON: {0}"
                        ).format(str(exc))
                    ]
                }
            )

    if not isinstance(value, dict):
        raise toolkit.ValidationError(
            {
                "schema": [
                    toolkit._(
                        "The Frictionless schema must be a JSON object."
                    )
                ]
            }
        )

    return value


def _get_boolean(value, field_name, default=None):
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, int) and value in (0, 1):
        return bool(value)

    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"false", "0", "no", "off"}:
        return False

    raise toolkit.ValidationError(
        {
            field_name: [
                toolkit._(
                    "The value must be true or false."
                )
            ]
        }
    )


def _raise_duplicate_name():
    raise toolkit.ValidationError(
        {
            "name": [
                toolkit._(
                    "A validation configuration with this name "
                    "already exists."
                )
            ]
        }
    )


def validation_configuration_create(context, data_dict):
    """Create a reusable Frictionless validation configuration."""
    toolkit.check_access(
        "validation_configuration_create",
        context,
        data_dict,
    )

    name = _get_name(data_dict)
    schema_descriptor = _get_schema_descriptor(data_dict)
    description = _get_description(data_dict)
    active = _get_boolean(
        data_dict.get("active"),
        "active",
        default=True,
    )

    try:
        configuration = ValidationConfiguration.create(
            name=name,
            description=description,
            schema_descriptor=schema_descriptor,
            active=active,
        )
    except IntegrityError:
        Session.rollback()
        _raise_duplicate_name()

    return configuration.as_dict()


@toolkit.side_effect_free
def validation_configuration_show(context, data_dict):
    """Return one validation configuration."""
    toolkit.check_access(
        "validation_configuration_show",
        context,
        data_dict,
    )

    configuration_id = toolkit.get_or_bust(
        data_dict,
        "id",
    )

    configuration = _get_configuration(
        configuration_id
    )

    return configuration.as_dict()


@toolkit.side_effect_free
def validation_configuration_list(context, data_dict):
    """Return validation configurations ordered by name."""
    toolkit.check_access(
        "validation_configuration_list",
        context,
        data_dict,
    )

    active = None

    if "active" in data_dict:
        active = _get_boolean(
            data_dict.get("active"),
            "active",
        )

    configurations = ValidationConfiguration.get_all(
        active=active
    )

    return [
        configuration.as_dict()
        for configuration in configurations
    ]


def validation_configuration_update(context, data_dict):
    """Update an existing validation configuration."""
    toolkit.check_access(
        "validation_configuration_update",
        context,
        data_dict,
    )

    configuration_id = toolkit.get_or_bust(
        data_dict,
        "id",
    )

    configuration = _get_configuration(
        configuration_id
    )

    values = {}

    if "name" in data_dict:
        values["name"] = _get_name(data_dict)

    if "description" in data_dict:
        values["description"] = _get_description(
            data_dict
        )

    if (
        "schema" in data_dict
        or "schema_descriptor" in data_dict
    ):
        values["schema_descriptor"] = (
            _get_schema_descriptor(data_dict)
        )

    if "active" in data_dict:
        values["active"] = _get_boolean(
            data_dict.get("active"),
            "active",
        )

    if not values:
        return configuration.as_dict()

    try:
        configuration.update_values(**values)
    except IntegrityError:
        Session.rollback()
        _raise_duplicate_name()

    return configuration.as_dict()


def validation_configuration_delete(context, data_dict):
    """Delete an existing validation configuration."""
    toolkit.check_access(
        "validation_configuration_delete",
        context,
        data_dict,
    )

    configuration_id = toolkit.get_or_bust(
        data_dict,
        "id",
    )

    configuration = _get_configuration(
        configuration_id
    )

    result = configuration.as_dict()

    ValidationConfiguration.delete_by_id(
        configuration_id
    )

    return result
