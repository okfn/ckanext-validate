from copy import deepcopy

from frictionless import Schema

from ckan.plugins import toolkit


def schema_from_descriptor(descriptor):
    """Create a Frictionless Schema from a stored descriptor.

    No field types, formats, or constraints are interpreted by this
    extension. Frictionless is responsible for validating and loading
    the complete descriptor.
    """
    if not isinstance(descriptor, dict):
        raise toolkit.ValidationError(
            {
                "schema": [
                    toolkit._(
                        "The validation schema must be a JSON object."
                    )
                ]
            }
        )

    try:
        return Schema.from_descriptor(deepcopy(descriptor))
    except Exception as exc:
        raise toolkit.ValidationError(
            {
                "schema": [
                    toolkit._(
                        "Invalid Frictionless schema: {0}"
                    ).format(str(exc))
                ]
            }
        )


def normalize_schema_descriptor(descriptor):
    """Validate and return the canonical Frictionless descriptor.

    Creating the Schema verifies the descriptor using Frictionless.
    Exporting it again ensures that only a valid, normalized descriptor
    is stored in the database.
    """
    schema = schema_from_descriptor(descriptor)
    return schema.to_descriptor()
