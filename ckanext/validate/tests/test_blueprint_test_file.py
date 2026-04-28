"""
Tests for the /ckan-admin/testfile admin view.

Covers:
  - Access control: only sysadmins can access the view (anonymous and regular
    users get 403).
  - GET: the form renders correctly for a sysadmin.
  - POST without a file shows the expected error.
  - POST with a non-CSV file shows the expected error.
  - POST with a valid CSV returns a success alert.
  - POST with an invalid CSV returns an error table (row / field / message).
  - POST with an invalid CSV that has no task-level errors shows the generic
    structural-error message.

Authentication uses API tokens (SysadminWithToken / UserWithToken) so that
Flask-WTF CSRF protection is automatically bypassed for POST requests.
"""

import io
import pytest
from types import SimpleNamespace
from unittest import mock

from ckan.tests import factories

from ckanext.validate.blueprints import resource as validate_resource
from .conftest import DummyReport

TEST_FILE_URL = "/ckan-admin/testfile"


# ---------------------------------------------------------------------------
# Access-control tests
# ---------------------------------------------------------------------------


class TestTestFileViewAccess:
    """Only sysadmins should be able to reach /ckan-admin/testfile."""

    def test_anonymous_user_is_forbidden(self, app):
        response = app.get(TEST_FILE_URL, status=403)
        assert "Need to be system administrator to administer" in response

    def test_regular_user_is_forbidden(self, app):
        user = factories.UserWithToken()

        response = app.get(
            TEST_FILE_URL,
            headers={"Authorization": user["token"]},
            status=403,
        )

        assert "Need to be system administrator to administer" in response

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
    """Patch frictionless Resource and system inside the blueprint module."""

    class _FakeResource:
        def __init__(self, *a, **kw):
            pass

        def validate(self):
            return report

    ctx_mgr = mock.MagicMock()
    ctx_mgr.__enter__.return_value = ctx_mgr
    ctx_mgr.__exit__.return_value = False

    fake_system = mock.MagicMock()
    fake_system.use_context.return_value = ctx_mgr

    monkeypatch.setattr(validate_resource, "Resource", _FakeResource)
    monkeypatch.setattr(validate_resource, "system", fake_system)


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

        assert "alert-success" in response
        assert "alert-danger" not in response
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

        assert "alert-danger" in response
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

        assert "alert-danger" in response
        assert "bad.csv" in response
        assert "Structural validation error" in response

    def test_post_validation_exception_shows_system_error(
        self, app, monkeypatch, auth_headers
    ):
        class BrokenResource:
            def __init__(self, *args, **kwargs):
                pass

            def validate(self):
                raise RuntimeError("boom")

        monkeypatch.setattr(validate_resource, "Resource", BrokenResource)

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
