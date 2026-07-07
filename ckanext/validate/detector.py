from datetime import datetime
from decimal import Decimal, InvalidOperation

from frictionless import Detector


DATE_FORMATS = [
    "%m/%d/%Y",  # 4/25/2024
    "%d/%m/%Y",  # 25/4/2024
    "%Y-%m-%d",  # 2024-04-25
]


def _to_decimal(value):
    value = "" if value is None else str(value).strip()

    if not value:
        return None

    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _to_date(value, date_format):
    value = "" if value is None else str(value).strip()

    if not value:
        return None

    try:
        return datetime.strptime(value, date_format).date()
    except ValueError:
        return None


def _majority_numeric_type(values, confidence):
    """Detect whether most values in a column are numeric.

    Every value is parsed using ``Decimal`` so that integer and decimal
    values can be detected without relying on floating-point conversion.

    The column is considered numeric only when the proportion of values
    successfully parsed as numbers is greater than or equal to
    ``confidence``.

    Returns:
        ``"integer"`` when every numeric value is a whole number.
        ``"number"`` when at least one numeric value has decimals.
        ``None`` when the required confidence is not reached.

    Example:
        Given the values::

            100
            250.50
            300
            invalid

        the column is detected as ``number`` when the configured confidence
        allows the three numeric values to represent the majority.

        Frictionless will then report ``invalid`` as a type error during
        resource validation.
    """
    if not values:
        return None

    parsed_values = [_to_decimal(value) for value in values]
    numeric_values = [value for value in parsed_values if value is not None]

    if len(numeric_values) / len(values) < confidence:
        return None

    if all(value == value.to_integral_value() for value in numeric_values):
        return "integer"

    return "number"


def _date_format(values, confidence):
    """Detect the date format used by most values in a column.

    Each value is tested against the supported formats defined in
    ``DATE_FORMATS``:

        - ``%m/%d/%Y``: month/day/year
        - ``%d/%m/%Y``: day/month/year
        - ``%Y-%m-%d``: year-month-day

    The format matching the largest number of values is selected. It is
    returned only when its match ratio is greater than or equal to
    ``confidence``.

    Once a format is selected, the complete column is validated using that
    format. Values that do not conform to it are reported by Frictionless as
    type or format errors.

    Returns:
        The detected ``strptime`` format, or ``None`` when no format reaches
        the configured confidence.
    """
    if not values:
        return None

    best_format = None
    best_count = 0

    for date_format in DATE_FORMATS:
        parsed_values = [_to_date(value, date_format) for value in values]
        date_values = [value for value in parsed_values if value is not None]

        if len(date_values) > best_count:
            best_count = len(date_values)
            best_format = date_format

    if best_count / len(values) < confidence:
        return None

    return best_format


class ValidateDetector(Detector):
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

            date_format = _date_format(
                values,
                confidence=self.field_confidence,
            )

            if date_format:
                detected_schema.set_field_type(field.name, "date")
                detected_schema.get_field(field.name).format = date_format
                continue

            numeric_type = _majority_numeric_type(
                values,
                confidence=self.field_confidence,
            )

            if numeric_type:
                detected_schema.set_field_type(field.name, numeric_type)

        return detected_schema
