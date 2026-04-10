import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.validate.actions import action as validate_action
from ckanext.validate.auth import validation as validate_auth
from ckanext.validate.blueprints import resource as validate_blueprint
from ckanext.validate import resource_hooks


class ValidatePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IResourceController)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "validate")

    # IActions

    def get_actions(self):
        return {
            "resource_validate": validate_action.resource_validate,
            "resource_validation_show": validate_action.resource_validation_show,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            "resource_validate": validate_auth.resource_validate,
            "resource_validation_show": validate_auth.resource_validation_show,
        }

    # IBlueprint

    def get_blueprint(self):
        return [validate_blueprint.resource_validate_blueprint]

    # IResourceController

    def after_resource_create(self, context, resource):
        resource_hooks.handle_resource_change(
            context=context,
            resource_dict=resource,
            operation="create",
        )

    def after_resource_update(self, context, resource):
        resource_hooks.handle_resource_change(
            context=context,
            resource_dict=resource,
            operation="update",
        )
