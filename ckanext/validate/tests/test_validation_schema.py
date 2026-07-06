import pytest

from ckan.plugins import toolkit

from ckanext.validate.validation_schema import (
    normalize_schema_descriptor,
    schema_from_descriptor,
)


def test_schema_from_descriptor_creates_frictionless_schema():
    descriptor = {
        "fields": [
            {
                "name": "id",
                "type": "integer",
                "constraints": {
                    "required": True,
                    "unique": True,
                },
            },
            {
                "name": "nombre",
                "type": "string",
                "constraints": {
                    "required": True,
                    "minLength": 2,
                },
            },
        ]
    }

    schema = schema_from_descriptor(descriptor)

    assert schema.field_names == ["id", "nombre"]
    assert schema.field_types == ["integer", "string"]

    id_field = schema.get_field("id")
    assert id_field.constraints["required"] is True
    assert id_field.constraints["unique"] is True


def test_normalize_schema_descriptor_returns_descriptor():
    descriptor = {
        "fields": [
            {
                "name": "monto",
                "type": "number",
                "constraints": {
                    "minimum": 0,
                },
            }
        ]
    }

    normalized = normalize_schema_descriptor(descriptor)

    assert normalized["fields"][0]["name"] == "monto"
    assert normalized["fields"][0]["type"] == "number"
    assert (
        normalized["fields"][0]["constraints"]["minimum"]
        == 0
    )


def test_schema_descriptor_must_be_a_dictionary():
    with pytest.raises(toolkit.ValidationError):
        schema_from_descriptor(
            ["this", "is", "not", "a", "schema"]
        )


def test_invalid_frictionless_schema_is_rejected():
    descriptor = {
        "fields": "invalid"
    }

    with pytest.raises(toolkit.ValidationError):
        schema_from_descriptor(descriptor)


def test_normalize_preserves_private_validation_rules():
    rules = [
        {
            "id": "rule-1",
            "field": "monto",
            "fieldType": "number",
            "constraint": "minimum",
            "value": 0,
            "message": "El monto no puede ser negativo",
            "enabled": False,
        }
    ]

    descriptor = {
        "fields": [
            {
                "name": "monto",
                "type": "number",
            }
        ],
        "_validate_rules": rules,
    }

    normalized = normalize_schema_descriptor(descriptor)

    assert normalized["_validate_rules"] == rules