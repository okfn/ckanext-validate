import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.validate.actions import action as validate_action
from ckanext.validate.auth import validation as validate_auth
from ckanext.validate.blueprints import resource, admin
from ckanext.validate import resource_hooks
from ckanext.validate import helpers as h


log = logging.getLogger(__name__)


class ValidatePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

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
        return [
            resource.resource_validate_blueprint,
            resource.validate_test_file_blueprint,
            admin.validation_jobs_blueprint,
        ]

    # IResourceController

    def after_resource_create(self, context, resource):
        resource_hooks.handle_resource_change(resource)

    def before_resource_update(self, context, current_resource, updated_resource):
        if updated_resource.get('upload'):
            log.debug("Resource file changed, triggering validation for resource %s", updated_resource.get("id"))
            resource_hooks.handle_resource_change(updated_resource)

    # ITemplateHelpers

    def get_helpers(self):
        return {
            "get_resource_validation_state": h.get_resource_validation_state,
            "get_resource_validation_job_status": h.get_resource_validation_job_status,
        }
