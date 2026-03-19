# Usage

## Database migration

After installing the plugin, run the migration to create the `resource_validation` table:

```bash
ckan db upgrade -p validate
```

This creates the `resource_validation` table used to store validation history.

---

## How it works

- Only **CSV** resources can be validated.
- Each validation run is stored as a new row in `resource_validation` — previous results are **not overwritten**, so a full history is kept.
- In addition to the dedicated table, the resource extras (`validation_status`, `validation_error_count`, `validation_errors`) are also updated for backwards compatibility.

---

## API Actions

### `resource_validate`

Validates a CSV resource using Frictionless and persists the result.

**Permissions:** requires `resource_update` on the resource.

**Parameters:**

| Name | Type   | Required | Description          |
|------|--------|----------|----------------------|
| `id` | string | yes      | The resource id      |

**Example:**

```bash
curl -X POST \
  -H "Authorization: <your-api-token>" \
  -H "Content-Type: application/json" \
  -d '{"id": "<resource-id>"}' \
  "http://localhost:5000/api/3/action/resource_validate"
```

**Response:** the updated resource dict with `validation_status` and `validation_error_count` fields.

---

### `resource_validation_show`

Returns the latest validation result for a given resource.

**Permissions:** public for any user who can view the resource.

**Parameters:**

| Name | Type   | Required | Description     |
|------|--------|----------|-----------------|
| `id` | string | yes      | The resource id |

**Example:**

```bash
curl -X POST \
  -H "Authorization: <your-api-token>" \
  -H "Content-Type: application/json" \
  -d '{"id": "<resource-id>"}' \
  "http://localhost:5000/api/3/action/resource_validation_show"
```

**Response:**

```json
{
  "success": true,
  "result": {
    "id": 1,
    "resource_id": "<resource-id>",
    "status": "failure",
    "error_count": 2,
    "errors": [
      {
        "row": 5,
        "field": "date",
        "message": "Type error in the cell \"abc\" in row \"5\" and field \"date\""
      }
    ],
    "created": "2026-03-19T14:50:32.364757"
  }
}
```

Raises `ObjectNotFound` (HTTP 404) if no validation has been run for the resource yet.

---

## Validation result fields

| Field         | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| `id`          | integer | Auto-incremented primary key                     |
| `resource_id` | string  | CKAN resource UUID                               |
| `status`      | string  | `"success"` or `"failure"`                       |
| `error_count` | integer | Number of validation errors found                |
| `errors`      | list    | List of error objects with `row`, `field`, `message` |
| `created`     | string  | ISO 8601 UTC timestamp of when the run occurred  |
