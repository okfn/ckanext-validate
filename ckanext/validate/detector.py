from decimal import Decimal, InvalidOperation

from frictionless import Detector


DETECTOR_FIELD_CONFIDENCE = 0.5
DEFAULT_MISSING_VALUES = ["null", "NULL", "None"]


def _to_decimal(value):
    value = "" if value is None else str(value).strip()

    if not value:
        return None

    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _majority_numeric_type(values, confidence):
    if not values:
        return None

    parsed_values = [_to_decimal(value) for value in values]
    numeric_values = [value for value in parsed_values if value is not None]

    if len(numeric_values) / len(values) < confidence:
        return None

    if all(value == value.to_integral_value() for value in numeric_values):
        return "integer"

    return "number"


class MajorityDetector(Detector):
    """
    Detector that fixes mostly numeric columns inferred as text.

    Frictionless can infer a column as string when it contains mixed values,
    for example:

        MONTO_PRESUPUESTADO
        20000
        8182.8
        Twelve
        250000

    In that case, the default detector may choose "string" and the text value
    would be accepted as valid.

    This detector keeps Frictionless' normal schema inference, but after that
    it checks fields inferred as "string" or "any". If most values in one of
    those fields are numeric, it changes the field type to "integer" or
    "number".

    Then, when Frictionless validates the resource, text values like "Twelve"
    are reported as type errors.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the detector with project defaults."""
        kwargs.setdefault("field_missing_values", DEFAULT_MISSING_VALUES)
        kwargs.setdefault("field_confidence", DETECTOR_FIELD_CONFIDENCE)
        super().__init__(*args, **kwargs)

    def detect_schema(
        self,
        fragment,
        *,
        labels=None,
        schema=None,
        field_candidates=None,
        **options,
    ):
        """Infer the schema and adjust mostly numeric string fields.

        Steps:
            1. Run the default Frictionless schema detection.
            2. If an explicit schema was provided, return it unchanged.
            3. Review only fields detected as "string" or "any".
            4. If most values in that field are numeric, update the schema type.
            5. Return the updated schema.

        Important:
            The field type must be changed with schema.set_field_type().
            Direct assignment like field.type = "number" raises a
            FrictionlessException.
        """
        detected_schema = super().detect_schema(
            fragment,
            labels=labels,
            schema=schema,
            field_candidates=field_candidates,
            **options,
        )

        if schema and schema.fields:
            return detected_schema

        missing_values = set(self.field_missing_values or [])

        for index, field in enumerate(detected_schema.fields):
            if field.type not in ("string", "any"):
                continue

            values = [
                row[index]
                for row in fragment
                if len(row) > index
                and str(row[index]).strip() not in missing_values
            ]

            numeric_type = _majority_numeric_type(
                values,
                confidence=self.field_confidence,
            )

            if numeric_type:
                detected_schema.set_field_type(field.name, numeric_type)

        return detected_schema
