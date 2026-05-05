import pytest

from ckan.tests import factories

VALIDATION_JOBS_URL = "/ckan-admin/validation-jobs"


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
class TestValidationJobsViewAccess:
    """Only sysadmins should be able to reach /ckan-admin/validation-jobs."""

    def test_anonymous_user_is_forbidden(self, app):
        response = app.get(VALIDATION_JOBS_URL, status=403)
        assert "Need to be system administrator to administer" in response

    def test_regular_user_is_forbidden(self, app):
        user = factories.UserWithToken()

        response = app.get(
            VALIDATION_JOBS_URL,
            headers={"Authorization": user["token"]},
            status=403,
        )

        assert "Need to be system administrator to administer" in response

    def test_sysadmin_can_access(self, app):
        sysadmin = factories.SysadminWithToken()

        response = app.get(
            VALIDATION_JOBS_URL,
            headers={"Authorization": sysadmin["token"]},
            status=200,
        )

        assert "Validation Jobs" in response
