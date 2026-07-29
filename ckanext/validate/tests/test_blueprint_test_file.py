"""
Tests for the /testfile CSV validation view.

Covers:
  - Access control: organization editors, organization admins and sysadmins
    can access the view.
  - Anonymous users, regular users and organization members receive 403.
  - GET renders the CSV validation form.
  - POST without a file shows the expected error.
  - POST with a non-CSV file shows the expected error.
  - POST with a valid CSV returns a success result.
  - POST with an invalid CSV returns grouped validation errors.

Authentication uses API tokens so Flask-WTF CSRF protection is bypassed for
the POST requests used by these functional tests.
"""

import io
import os
import pytest
from types import SimpleNamespace

from ckan.tests import factories

from ckanext.validate.blueprints import resource as validate_resource
from .conftest import DummyReport

TEST_FILE_URL = "/testfile"


# ---------------------------------------------------------------------------
# Access-control tests
# ---------------------------------------------------------------------------


class TestTestFileViewAccess:
    """Editors, organization admins and sysadmins can access /testfile."""

    forbidden_message = (
        "You must be an editor or administrator to validate a file."
    )

    def test_anonymous_user_is_forbidden(self, app):
        response = app.get(
            TEST_FILE_URL,
            status=403,
        )

        assert self.forbidden_message in response

    def test_regular_user_is_forbidden(self, app):
        user = factories.UserWithToken()

        response = app.get(
            TEST_FILE_URL,
            headers={"Authorization": user["token"]},
            status=403,
        )

        assert self.forbidden_message in response

    def test_organization_member_is_forbidden(self, app):
        member = factories.UserWithToken()

        factories.Organization(
            users=[
                {
                    "name": member["name"],
                    "capacity": "member",
                }
            ]
        )

        response = app.get(
            TEST_FILE_URL,
            headers={"Authorization": member["token"]},
            status=403,
        )

        assert self.forbidden_message in response

    def test_organization_editor_can_access(self, app):
        editor = factories.UserWithToken()

        factories.Organization(
            users=[
                {
                    "name": editor["name"],
                    "capacity": "editor",
                }
            ]
        )

        response = app.get(
            TEST_FILE_URL,
            headers={"Authorization": editor["token"]},
            status=200,
        )

        assert "Validate a CSV File" in response
        assert "Select a CSV File for Validation" in response

    def test_organization_admin_can_access(self, app):
        organization_admin = factories.UserWithToken()

        factories.Organization(
            users=[
                {
                    "name": organization_admin["name"],
                    "capacity": "admin",
                }
            ]
        )

        response = app.get(
            TEST_FILE_URL,
            headers={"Authorization": organization_admin["token"]},
            status=200,
        )

        assert "Validate a CSV File" in response

    def test_sysadmin_can_access(self, app):
        sysadmin = factories.SysadminWithToken()

        response = app.get(
            TEST_FILE_URL,
            headers={"Authorization": sysadmin["token"]},
            status=200,
        )

        assert "Validate a CSV File" in response
        assert "Select a CSV File for Validation" in response


# ---------------------------------------------------------------------------
# Helpers shared by the POST tests
# ---------------------------------------------------------------------------


def _mock_frictionless(monkeypatch, report):
    """Patch get_validation_report inside the blueprint module."""

    def fake_get_validation_report(source, format):
        return report

    monkeypatch.setattr(
        validate_resource,
        "get_validation_report",
        fake_get_validation_report,
    )

# ---------------------------------------------------------------------------
# Functional POST tests
# ---------------------------------------------------------------------------


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
class TestTestFileViewPost:
    """File-upload and CSV-validation logic for the test_file view."""

    @pytest.fixture
    def auth_headers(self):
        sysadmin = factories.SysadminWithToken()
        return {"Authorization": sysadmin["token"]}

    # --- upload validation ------------------------------------------------

    def test_post_without_file_shows_error(self, app, auth_headers):
        response = app.post(
            TEST_FILE_URL,
            data={},
            headers=auth_headers,
            status=200,
        )

        assert "Please select a CSV file" in response

    def test_post_non_csv_shows_error(self, app, auth_headers):
        data = {"file": (io.BytesIO(b"some content"), "report.xlsx")}

        response = app.post(
            TEST_FILE_URL,
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
            status=200,
        )

        assert "Only CSV files are supported" in response

    # --- frictionless validation: success ---------------------------------

    def test_post_valid_csv_shows_success_alert(
        self, app, monkeypatch, auth_headers
    ):
        report = DummyReport(valid=True, tasks=[])
        _mock_frictionless(monkeypatch, report)

        data = {"file": (io.BytesIO(b"id,name\n1,Alice\n2,Bob\n"), "data.csv")}

        response = app.post(
            TEST_FILE_URL,
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
            status=200,
        )

        assert "validate-badge--valid" in response
        assert "validate-badge--invalid" not in response
        assert "data.csv" in response

    # --- frictionless validation: failure ---------------------------------

    def test_post_invalid_csv_shows_error_table(
        self, app, monkeypatch, auth_headers
    ):
        err1 = SimpleNamespace(
            row_number=3,
            field_name="price",
            message="invalid type in price",
        )
        err2 = SimpleNamespace(
            row_number=5,
            field_name="stock",
            message="missing required value",
        )

        report = DummyReport(
            valid=False,
            tasks=[SimpleNamespace(errors=[err1, err2])],
        )
        _mock_frictionless(monkeypatch, report)

        data = {"file": (io.BytesIO(b"id,price,stock\n1,bad,\n"), "bad.csv")}

        response = app.post(
            TEST_FILE_URL,
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
            status=200,
        )

        assert "validate-badge--invalid" in response
        assert "bad.csv" in response
        assert "price" in response
        assert "stock" in response
        assert "invalid type in price" in response
        assert "missing required value" in response

    def test_post_invalid_csv_without_task_errors_shows_structural_message(
        self, app, monkeypatch, auth_headers
    ):
        report = DummyReport(
            valid=False,
            tasks=[SimpleNamespace(errors=[])],
        )
        _mock_frictionless(monkeypatch, report)

        data = {"file": (io.BytesIO(b"malformed"), "bad.csv")}

        response = app.post(
            TEST_FILE_URL,
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
            status=200,
        )

        assert "validate-badge--invalid" in response
        assert "bad.csv" in response
        assert "Structural validation error" in response

    def test_post_validation_exception_shows_system_error(
        self, app, monkeypatch, auth_headers
    ):
        def fake_get_validation_report(source, format):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            validate_resource,
            "get_validation_report",
            fake_get_validation_report,
        )

        data = {
            "file": (
                io.BytesIO(b"id,name\n1,Alice\n"),
                "broken.csv",
            )
        }

        response = app.post(
            TEST_FILE_URL,
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
            status=200,
        )

        assert "System error during validation: boom" in response

    def test_post_mostly_numeric_column_with_text_is_invalid_from_file(
        self, app, auth_headers
    ):
        """Regression test for #202: a mostly-numeric column with a text value
        should be treated as a type error, not a structural error."""

        csv_path = os.path.join(
            os.path.dirname(__file__), "files_test", "test_num_field.csv"
        )
        with open(csv_path, "rb") as f:
            csv_bytes = f.read()

        data = {
            "file": (
                io.BytesIO(csv_bytes),
                "test_num_field.csv",
            )
        }

        response = app.post(
            TEST_FILE_URL,
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
            status=200,
        )

        assert "validate-badge--invalid" in response
        assert "MONTO_PRESUPUESTADO" in response
        assert "type-error" in response or "Type error" in response
        assert "Twelve" in response

    def test_post_mostly_date_column_with_invalid_dates_is_invalid_from_file(
        self, app, auth_headers
    ):
        """Regression test: a mostly-date column with invalid date values
        should be treated as a type error, not inferred as text."""

        csv_path = os.path.join(
            os.path.dirname(__file__), "files_test", "test_date_field.csv"
        )
        with open(csv_path, "rb") as f:
            csv_bytes = f.read()

        data = {
            "file": (
                io.BytesIO(csv_bytes),
                "test_date_field.csv",
            )
        }

        response = app.post(
            TEST_FILE_URL,
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
            status=200,
        )

        assert "validate-badge--invalid" in response
        assert "Fecha de Firma" in response
        assert "type-error" in response or "Type error" in response
        assert "12/00/2020" in response
        assert "10/32/2022" in response
        assert "2/29/2021" in response
