from ckanext.validate.actions import action as validate_action
from ckanext.validate.auth import validation as validate_auth
from ckanext.validate.blueprints import resource as validate_resource
from ckanext.validate.plugin import ValidatePlugin


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
