import pytest

from ckan.plugins import toolkit
from ckan.tests import factories


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
class TestValidationJobsViewAccess:
    """Only sysadmins should be able to reach /ckan-admin/validation-jobs."""

    def test_anonymous_user_is_forbidden(self, app):
        url = toolkit.url_for("validate_admin.validation_jobs")
        response = app.get(url, status=403)
        assert "Need to be system administrator to administer" in response

    def test_regular_user_is_forbidden(self, app):
        user = factories.UserWithToken()
        url = toolkit.url_for("validate_admin.validation_jobs")

        response = app.get(
            url,
            headers={"Authorization": user["token"]},
            status=403,
        )

        assert "Need to be system administrator to administer" in response

    def test_sysadmin_can_access(self, app):
        sysadmin = factories.SysadminWithToken()
        url = toolkit.url_for("validate_admin.validation_jobs")

        response = app.get(
            url,
            headers={"Authorization": sysadmin["token"]},
            status=200,
        )

        assert "Validation Jobs" in response
