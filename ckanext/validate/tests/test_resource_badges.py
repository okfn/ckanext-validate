import pytest

from ckan.tests import factories

from ckanext.validate.model.validation import Validation
from ckanext.validate import resource_hooks


@pytest.fixture(autouse=True)
def disable_auto_validation(monkeypatch):
    monkeypatch.setattr(resource_hooks, "handle_resource_change", lambda *a, **kw: False)


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
def test_dataset_page_hides_validation_badge_for_anonymous_user(app):
    dataset = factories.Dataset()
    resource = factories.Resource(
        package_id=dataset["id"],
        format="CSV",
        name="validated-resource",
    )

    Validation.create(
        resource_id=resource["id"],
        status="success",
        error_count=0,
        errors=[],
    )

    response = app.get(f"/dataset/{dataset['name']}", status=200)

    assert "validated-resource" in response
    assert "validate-badge--valid" not in response
    assert "Valid" not in response


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
def test_dataset_page_shows_validation_badge_for_sysadmin(app):
    sysadmin = factories.SysadminWithToken()
    dataset = factories.Dataset()
    resource = factories.Resource(
        package_id=dataset["id"],
        format="CSV",
        name="validated-resource",
    )

    Validation.create(
        resource_id=resource["id"],
        status="success",
        error_count=0,
        errors=[],
    )

    response = app.get(
        f"/dataset/{dataset['name']}",
        headers={"Authorization": sysadmin["token"]},
        status=200,
    )

    assert "validated-resource" in response
    assert "validate-badge--valid" in response
    assert "Valid" in response
