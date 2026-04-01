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
from ckanext.validate.blueprints import resource as validate_resource
from ckanext.validate.plugin import ValidatePlugin


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
def test_plugin():
    assert plugin_loaded("validate")


def test_plugin_registers_expected_blueprint():
    plugin = ValidatePlugin()

    blueprints = plugin.get_blueprint()

    assert blueprints == [validate_resource.resource_validate_blueprint]


def test_plugin_after_resource_create_delegates_to_resource_hooks(monkeypatch):
    captured = {}

    def fake_handle_resource_change(context, resource_dict, operation):
        captured["context"] = context
        captured["resource_dict"] = resource_dict
        captured["operation"] = operation

    monkeypatch.setattr(resource_hooks, "handle_resource_change", fake_handle_resource_change)

    username = "alice"
    plugin = ValidatePlugin()
    plugin.after_resource_create({"user": username}, {"id": "res-1", "format": "CSV"})

    assert captured == {
        "context": {"user": username},
        "resource_dict": {"id": "res-1", "format": "CSV"},
        "operation": "create",
    }


def test_plugin_after_resource_update_delegates_to_resource_hooks(monkeypatch):
    captured = {}

    def fake_handle_resource_change(context, resource_dict, operation):
        captured["context"] = context
        captured["resource_dict"] = resource_dict
        captured["operation"] = operation

    monkeypatch.setattr(resource_hooks, "handle_resource_change", fake_handle_resource_change)

    username = "alice"
    plugin = ValidatePlugin()
    plugin.after_resource_update({"user": username}, {"id": "res-2", "format": "CSV"})

    assert captured == {
        "context": {"user": username},
        "resource_dict": {"id": "res-2", "format": "CSV"},
        "operation": "update",
    }


def test_plugin_before_resource_show_returns_resource_dict():
    plugin = ValidatePlugin()
    resource = {"id": "res-3"}

    assert plugin.before_resource_show(resource) == resource


def test_plugin_before_resource_create_returns_resource_dict():
    plugin = ValidatePlugin()
    resource = {"id": "res-4"}

    assert plugin.before_resource_create({}, resource) == resource


def test_plugin_before_resource_update_returns_resource_dict():
    plugin = ValidatePlugin()
    current = {"id": "res-5"}
    resource = {"id": "res-5", "format": "CSV"}

    assert plugin.before_resource_update({}, current, resource) == resource


def test_plugin_delete_hooks_are_noops():
    plugin = ValidatePlugin()

    assert plugin.before_resource_delete({}, {"id": "res-6"}, [{"id": "res-6"}]) is None
    assert plugin.after_resource_delete({}, [{"id": "res-6"}]) is None
