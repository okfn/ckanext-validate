from copy import deepcopy

from frictionless import Schema

from ckan.plugins import toolkit


VALIDATION_RULES_PROPERTY = "_validate_rules"


def _frictionless_descriptor(descriptor):
    """Return only the descriptor properties interpreted by Frictionless.

    The visual editor stores UI-only information (custom messages and enabled
    state) in a private descriptor property. It must not participate in schema
    validation.
    """
    frictionless_descriptor = deepcopy(descriptor)
    frictionless_descriptor.pop(VALIDATION_RULES_PROPERTY, None)
    return frictionless_descriptor


def schema_from_descriptor(descriptor):
    """Create a Frictionless Schema from a stored descriptor."""
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
        return Schema.from_descriptor(
            _frictionless_descriptor(descriptor)
        )
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
    """Validate, normalize and return a Frictionless descriptor.

    Frictionless remains the source of truth for field types and constraints.
    The private ``_validate_rules`` property is preserved only for the visual
    editor because it contains information that Table Schema does not model,
    such as custom messages and disabled rules.
    """
    private_rules = deepcopy(
        descriptor.get(VALIDATION_RULES_PROPERTY)
    )

    schema = schema_from_descriptor(descriptor)
    normalized = schema.to_descriptor()

    if isinstance(private_rules, list):
        normalized[VALIDATION_RULES_PROPERTY] = private_rules

    return normalized
