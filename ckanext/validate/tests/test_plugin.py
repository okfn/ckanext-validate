"""
Tests for plugin.py.

Tests are written using the pytest library (https://docs.pytest.org), and you
should read the testing guidelines in the CKAN docs:
https://docs.ckan.org/en/2.9/contributing/testing.html

To write tests for your extension you should install the pytest-ckan package:

    pip install pytest-ckan

This will allow you to use CKAN specific fixtures on your tests.

For instance, if your test involves database access you can use `clean_db` to
reset the database:

    import pytest

    from ckan.tests import factories

    @pytest.mark.usefixtures("clean_db")
    def test_some_action():

        dataset = factories.Dataset()

        # ...

For functional tests that involve requests to the application, you can use the
`app` fixture:

    from ckan.plugins import toolkit

    def test_some_endpoint(app):

        url = toolkit.url_for('myblueprint.some_endpoint')

        response = app.get(url)

        assert response.status_code == 200


To temporary patch the CKAN configuration for the duration of a test you can use:

    import pytest

    @pytest.mark.ckan_config("ckanext.myext.some_key", "some_value")
    def test_some_action():
        pass
"""
import pytest
from ckan.plugins import plugin_loaded

from ckanext.validate import resource_hooks
from ckanext.validate.actions import action as validate_action
from ckanext.validate.auth import validation as validate_auth
from ckanext.validate.blueprints.resource import validate_test_file_blueprint
from ckanext.validate.blueprints import resource as validate_resource
from ckanext.validate.blueprints import admin as validate_admin
from ckanext.validate.plugin import ValidatePlugin


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
def test_plugin():
    assert plugin_loaded("validate")


def test_plugin_registers_expected_blueprint():
    plugin = ValidatePlugin()

    blueprints = plugin.get_blueprint()

    assert blueprints == [
        validate_resource.resource_validate_blueprint,
        validate_test_file_blueprint,
        validate_admin.validation_jobs_blueprint,
    ]


def test_plugin_registers_expected_actions():
    plugin = ValidatePlugin()

    assert plugin.get_actions() == {
        "resource_validate": validate_action.resource_validate,
        "resource_validation_show": validate_action.resource_validation_show,
        "validation_job_list": validate_action.validation_job_list,
    }


def test_plugin_registers_expected_auth_functions():
    plugin = ValidatePlugin()

    assert plugin.get_auth_functions() == {
        "resource_validate": validate_auth.resource_validate,
        "resource_validation_show": validate_auth.resource_validation_show,
        "validation_job_list": validate_auth.validation_job_list,
    }


def test_plugin_after_resource_create_delegates_to_resource_hooks(monkeypatch):
    captured = {}

    def fake_handle_resource_change(resource_dict):
        captured["resource_dict"] = resource_dict

    monkeypatch.setattr(resource_hooks, "handle_resource_change", fake_handle_resource_change)

    plugin = ValidatePlugin()
    plugin.after_resource_create({"user": "alice"}, {"id": "res-1", "format": "CSV"})

    assert captured == {
        "resource_dict": {"id": "res-1", "format": "CSV"},
    }


def test_validation_is_executed_if_new_upload_on_resource_update(monkeypatch):
    captured = {}

    def fake_handle_resource_change(resource_dict):
        captured["resource_dict"] = resource_dict

    monkeypatch.setattr(resource_hooks, "handle_resource_change", fake_handle_resource_change)

    plugin = ValidatePlugin()
    plugin.before_resource_update(
        {"user": "alice"},
        {"id": "res-1", "format": "CSV", "upload": None},
        {"id": "res-1", "format": "CSV", "upload": "new_file.csv"},
    )

    assert captured == {
        "resource_dict": {"id": "res-1", "format": "CSV", "upload": "new_file.csv"},
    }


def test_validation_is_not_executed_if_no_upload_on_resource_update(monkeypatch):
    called = {"handle_resource_change": False}

    def fake_handle_resource_change(resource_dict):
        called["handle_resource_change"] = True

    monkeypatch.setattr(resource_hooks, "handle_resource_change", fake_handle_resource_change)

    plugin = ValidatePlugin()
    plugin.before_resource_update(
        {"user": "alice"},
        {"id": "res-1", "format": "CSV", "upload": None},
        {"id": "res-1", "format": "TSV", "upload": None, "name": "Resource 1"},
    )

    assert called == {"handle_resource_change": False}


def test_plugin_registers_expected_helpers():
    plugin = ValidatePlugin()

    helpers = plugin.get_helpers()

    assert "get_resource_validation_state" in helpers
    assert "get_resource_validation_job_status" in helpers


def test_plugin_delete_hooks_are_noops():
    plugin = ValidatePlugin()

    assert plugin.before_resource_delete({}, {"id": "res-6"}, [{"id": "res-6"}]) is None
    assert plugin.after_resource_delete({}, [{"id": "res-6"}]) is None
