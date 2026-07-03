import pytest

from ckan.plugins import toolkit

from ckanext.validate.model.validation_configuration import (
    ValidationConfiguration,
)


pytestmark = pytest.mark.usefixtures("clean_db")


def _schema_descriptor():
    return {
        "fields": [
            {
                "name": "codigo",
                "type": "string",
                "constraints": {
                    "required": True,
                },
            },
            {
                "name": "fecha",
                "type": "date",
                "format": "%Y-%m-%d",
            },
            {
                "name": "monto",
                "type": "number",
                "constraints": {
                    "minimum": 0,
                },
            },
        ],
        "missingValues": [""],
    }


def test_create_validation_configuration():
    configuration = ValidationConfiguration.create(
        name="Procesos de adquisiciones",
        description="Validación de procesos",
        schema_descriptor=_schema_descriptor(),
    )

    assert configuration.id
    assert configuration.name == "Procesos de adquisiciones"
    assert configuration.active is True

    stored = ValidationConfiguration.get(
        configuration.id
    )

    assert stored is not None
    assert stored.name == configuration.name
    assert stored.schema_descriptor["fields"][0]["name"] == (
        "codigo"
    )


def test_configuration_returns_frictionless_schema():
    """Test that the Frictionless Schema is returned from the stored descriptor."""
    configuration = ValidationConfiguration.create(
        name="Configuración de prueba",
        schema_descriptor=_schema_descriptor(),
    )

    schema = configuration.get_schema()

    assert schema.field_names == [
        "codigo",
        "fecha",
        "monto",
    ]

    assert schema.get_field("fecha").type == "date"
    assert schema.get_field("monto").type == "number"


def test_invalid_schema_is_not_saved():
    """Test that an invalid schema descriptor raises a ValidationError and is not saved."""
    with pytest.raises(toolkit.ValidationError):
        ValidationConfiguration.create(
            name="Configuración inválida",
            schema_descriptor={
                "fields": "invalid",
            },
        )

    assert (
        ValidationConfiguration.get_by_name(
            "Configuración inválida"
        )
        is None
    )


def test_list_only_active_configurations():
    """Test that get_all() returns only active configurations when active=True is passed."""
    active_configuration = ValidationConfiguration.create(
        name="Activa",
        schema_descriptor=_schema_descriptor(),
        active=True,
    )

    ValidationConfiguration.create(
        name="Inactiva",
        schema_descriptor=_schema_descriptor(),
        active=False,
    )

    configurations = ValidationConfiguration.get_all(
        active=True
    )

    assert configurations == [active_configuration]


def test_update_schema_validates_new_descriptor():
    """Test that updating the schema descriptor validates the new descriptor and updates the stored schema."""
    configuration = ValidationConfiguration.create(
        name="Configuración",
        schema_descriptor=_schema_descriptor(),
    )

    configuration.update_values(
        schema_descriptor={
            "fields": [
                {
                    "name": "identificador",
                    "type": "integer",
                    "constraints": {
                        "required": True,
                    },
                }
            ]
        }
    )

    schema = configuration.get_schema()

    assert schema.field_names == ["identificador"]
    assert schema.field_types == ["integer"]


def test_update_rejects_invalid_schema():
    configuration = ValidationConfiguration.create(
        name="Configuración",
        schema_descriptor=_schema_descriptor(),
    )

    with pytest.raises(toolkit.ValidationError):
        configuration.update_values(
            schema_descriptor={
                "fields": "invalid",
            }
        )
