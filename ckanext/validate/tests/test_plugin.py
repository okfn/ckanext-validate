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
from ckanext.validate.actions import action as validate_action
from ckanext.validate.auth import validation as validate_auth
from ckanext.validate.blueprints import resource as validate_resource
from ckanext.validate.plugin import ValidatePlugin


@pytest.mark.ckan_config("ckan.plugins", "validate")
@pytest.mark.usefixtures("with_plugins")
def test_plugin():
    assert plugin_loaded("validate")


def test_plugin_registers_expected_actions():
    plugin = ValidatePlugin()

    actions = plugin.get_actions()

    assert actions == {
        "resource_validate": validate_action.resource_validate,
        "resource_validation_show": validate_action.resource_validation_show,
    }


def test_plugin_registers_expected_auth_functions():
    plugin = ValidatePlugin()

    auth_functions = plugin.get_auth_functions()

    assert auth_functions == {
        "resource_validate": validate_auth.resource_validate,
        "resource_validation_show": validate_auth.resource_validation_show,
    }


def test_plugin_registers_expected_blueprint():
    plugin = ValidatePlugin()

    blueprints = plugin.get_blueprint()

    assert blueprints == [validate_resource.resource_validate_blueprint]
