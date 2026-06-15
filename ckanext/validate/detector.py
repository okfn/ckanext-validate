from frictionless import Detector, Field, Schema, settings


class MajorityDetector(Detector):
    """Infer field types using all values available in the sample."""

    def detect_schema(
        self,
        fragment,
        *,
        labels=None,
        schema=None,
        field_candidates=None,
        **options,
    ):
        if schema and schema.fields:
            return super().detect_schema(
                fragment,
                labels=labels,
                schema=schema,
                field_candidates=(
                    field_candidates or settings.DEFAULT_FIELD_CANDIDATES
                ),
                **options,
            )

        candidates = (
            field_candidates or settings.DEFAULT_FIELD_CANDIDATES
        )

        skeleton = Detector(
            field_type="any",
            field_names=self.field_names,
        ).detect_schema(fragment, labels=labels)

        inferred_fields = []

        for index, name in enumerate(skeleton.field_names):
            values = [
                row[index]
                for row in fragment
                if len(row) > index
                and row[index] not in self.field_missing_values
            ]

            selected = {"name": name, "type": "string"}
            best_ratio = 0

            for candidate in candidates:
                # String accepts every CSV value, so use it only as fallback.
                if candidate.get("type") in ("string", "any"):
                    continue

                field_descriptor = candidate.copy()
                field_descriptor["name"] = name
                field = Field.from_descriptor(field_descriptor)

                valid_count = 0

                for value in values:
                    _, notes = field.read_cell(value)
                    if not notes:
                        valid_count += 1

                ratio = valid_count / len(values) if values else 0

                if (
                    ratio >= self.field_confidence
                    and ratio > best_ratio
                ):
                    selected = field.to_descriptor()
                    best_ratio = ratio

            inferred_fields.append(selected)

        descriptor = {"fields": inferred_fields}

        if self.field_missing_values != settings.DEFAULT_MISSING_VALUES:
            descriptor["missingValues"] = self.field_missing_values

        return Schema.from_descriptor(descriptor)
