"""
Tests for the /dataset/<package_id>/resource/<resource_id>/validate blueprint.

Covers:
  - GET: renders the validation page with the resource name.
  - GET: shows "Not validated" badge when no validation record exists.
  - GET: shows correct status badge (valid, invalid, pending, error).
  - GET: returns 404 for unknown package or resource.
  - POST: unauthorized user gets 403.
  - POST: triggers validation and renders the updated status badge.
  - POST: shows errors block when action raises ValidationError.

Authentication uses API tokens (SysadminWithToken / UserWithToken) so that
Flask-WTF CSRF protection is automatically bypassed for POST requests.
"""

import pytest

from ckan.tests import factories

from ckanext.validate.actions import action as validate_action
from ckanext.validate.model.validation import Validation
from ckanext.validate import resource_hooks
from .conftest import DummyReport


def _validate_url(package_name, resource_id):
    return f"/dataset/{package_name}/resource/{resource_id}/validate"


@pytest.fixture(autouse=True)
def disable_auto_validation(monkeypatch):
    """Prevent auto-validation hooks from firing when factories create CSV resources."""
    monkeypatch.setattr(resource_hooks, "handle_resource_change", lambda *a, **kw: False)


# ---------------------------------------------------------------------------
# GET tests
# ---------------------------------------------------------------------------


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
class TestResourceValidateGet:

    @pytest.fixture
    def sysadmin_headers(self):
        sysadmin = factories.SysadminWithToken()
        return {"Authorization": sysadmin["token"]}

    def test_get_renders_validation_page_with_resource_name(self, app):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package_id=dataset["id"], format="CSV", name="my-resource"
        )

        response = app.get(_validate_url(dataset["name"], resource["id"]), status=200)

        assert "Resource Validation" in response
        assert "my-resource" in response

    def test_get_shows_not_validated_badge_when_no_record(self, app, sysadmin_headers):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"], format="CSV")

        response = app.get(_validate_url(dataset["name"], resource["id"]), status=200, headers=sysadmin_headers)

        assert "validate-badge--pending" in response
        assert "Not validated" in response

    def test_get_shows_valid_badge_when_status_success(self, app, sysadmin_headers):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"], format="CSV")
        Validation.create(
            resource_id=resource["id"], status="success", error_count=0, errors=[]
        )

        response = app.get(_validate_url(dataset["name"], resource["id"]), status=200, headers=sysadmin_headers)

        assert "validate-badge--valid" in response

    def test_get_shows_invalid_badge_and_count_when_status_failure(self, app, sysadmin_headers):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"], format="CSV")
        Validation.create(
            resource_id=resource["id"], status="failure", error_count=4, errors=[]
        )

        response = app.get(_validate_url(dataset["name"], resource["id"]), status=200, headers=sysadmin_headers)

        assert "validate-badge--invalid" in response
        assert "4" in response

    def test_get_shows_pending_badge_when_status_pending(self, app, sysadmin_headers):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"], format="CSV")
        Validation.create(
            resource_id=resource["id"], status="pending", error_count=0, errors=[]
        )

        response = app.get(_validate_url(dataset["name"], resource["id"]), status=200, headers=sysadmin_headers)

        assert "validate-badge--pending" in response
        assert "Pending" in response

    def test_get_shows_error_badge_when_status_error(self, app, sysadmin_headers):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"], format="CSV")
        Validation.create(
            resource_id=resource["id"], status="error", error_count=0, errors=[]
        )

        response = app.get(_validate_url(dataset["name"], resource["id"]), status=200, headers=sysadmin_headers)

        assert "validate-badge--error" in response

    def test_get_returns_404_for_unknown_package(self, app):
        app.get(
            "/dataset/no-such-package/resource/no-such-id/validate", status=404
        )

    def test_get_returns_404_for_unknown_resource(self, app):
        dataset = factories.Dataset()
        app.get(
            f"/dataset/{dataset['name']}/resource/no-such-id/validate", status=404
        )


# ---------------------------------------------------------------------------
# POST tests
# ---------------------------------------------------------------------------


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
class TestResourceValidatePost:

    @pytest.fixture
    def sysadmin_headers(self):
        sysadmin = factories.SysadminWithToken()
        return {"Authorization": sysadmin["token"]}

    @pytest.fixture
    def user_headers(self):
        user = factories.UserWithToken()
        return {"Authorization": user["token"]}

    def test_post_unauthorized_user_is_forbidden(self, app, user_headers):
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        resource = factories.Resource(package_id=dataset["id"], format="CSV")

        response = app.post(
            _validate_url(dataset["name"], resource["id"]),
            data={},
            headers=user_headers,
            status=403,
        )

        assert "Not authorized" in response

    def test_post_renders_valid_badge_after_successful_validation(
        self, app, monkeypatch, sysadmin_headers
    ):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package_id=dataset["id"], format="CSV", url_type="", url="https://example.com/valid.csv"
        )

        monkeypatch.setattr(
            validate_action,
            "get_validation_report",
            lambda s, f, schema=None: DummyReport(valid=True, tasks=[]),
        )

        response = app.post(
            _validate_url(dataset["name"], resource["id"]),
            data={},
            headers=sysadmin_headers,
            status=200,
        )

        assert "validate-badge--valid" in response

    def test_post_renders_invalid_badge_after_failed_validation(
        self, app, monkeypatch, sysadmin_headers
    ):
        from types import SimpleNamespace

        dataset = factories.Dataset()
        resource = factories.Resource(
            package_id=dataset["id"], format="CSV", url_type="", url="https://example.com/bad.csv"
        )

        err = SimpleNamespace(row_number=2, field_name="price", message="type error")

        monkeypatch.setattr(
            validate_action,
            "get_validation_report",
            lambda s, f, schema=None: DummyReport(
                valid=False,
                tasks=[SimpleNamespace(errors=[err])],
            ),
        )

        response = app.post(
            _validate_url(dataset["name"], resource["id"]),
            data={},
            headers=sysadmin_headers,
            status=200,
        )

        assert "validate-badge--invalid" in response
        assert "1" in response

    def test_post_shows_errors_block_when_action_raises_validation_error(
        self, app, monkeypatch, sysadmin_headers
    ):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"], format="XLSX")

        response = app.post(
            _validate_url(dataset["name"], resource["id"]),
            data={},
            headers=sysadmin_headers,
            status=200,
        )

        assert "alert-danger" in response
        assert "format" in response
        assert "Only CSV resources can be validated." in response
