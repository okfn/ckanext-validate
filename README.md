[![Tests](https://github.com/okfn/ckanext-validate/workflows/Tests/badge.svg?branch=main)](https://github.com/okfn/ckanext-validate/actions)

# ckanext-validate

A simple CKAN extension to validate tabular data powered by [frictionless data](https://framework.frictionlessdata.io/).


## Requirements

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.10            | not tested    |
| 2.11            | yes           |


## Installation

To install ckanext-validate:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv

    git clone https://github.com/okfn/ckanext-validate.git
    cd ckanext-validate
    pip install -e .
	pip install -r requirements.txt

3. Add `validate` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Run the database migration to create the `resource_validation` table:

    ckan db upgrade -p validate

5. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload


## Usage

Only **CSV** resources can be validated. Each validation run is stored as a new row in `resource_validation` — previous results are **not overwritten**, so a full history is kept. In addition to the dedicated table, the resource extras (`validation_status`, `validation_error_count`, `validation_errors`) are also updated for backwards compatibility.

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

### Validation result fields

| Field         | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| `id`          | integer | Auto-incremented primary key                     |
| `resource_id` | string  | CKAN resource UUID                               |
| `status`      | string  | `"success"` or `"failure"`                       |
| `error_count` | integer | Number of validation errors found                |
| `errors`      | list    | List of error objects with `row`, `field`, `message` |
| `created`     | string  | ISO 8601 UTC timestamp of when the run occurred  |


## Config settings

### `ckanext.validate.fail_on_invalid_upload`

Controls whether CSV files are validated **synchronously** during resource
create and update.  When enabled, invalid files are rejected before being
saved, and the user receives a `ValidationError` with the details.

| | |
|---|---|
| **Type** | boolean |
| **Default** | `false` |

```ini
# Reject invalid CSV files on upload (optional, default: false).
ckanext.validate.fail_on_invalid_upload = false
```

**When `true`:**

* Uploaded CSV files are validated with Frictionless during
  `resource_create` and `resource_update`.
* If the file is invalid, a `ValidationError` is raised and the resource is
  **not** saved.
* The user receives a clear message listing the validation errors.
* Only applies to file uploads — URL-linked resources and metadata-only
  updates are unaffected.

**When `false` (default):**

* The existing behaviour is preserved: uploads are always accepted and
  validated asynchronously in the background via the job queue.

> **Note:** the default is `false` to preserve backwards compatibility.
> Enable this option only when your instance requires a strict upload policy.


## Developer installation

To install ckanext-validate for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/okfn/ckanext-validate.git
    cd ckanext-validate
    pip install -e .
    pip install -r dev-requirements.txt


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini


## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
