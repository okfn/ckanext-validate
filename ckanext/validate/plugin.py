import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.scheming.plugins import ISchemingDatasets


class ValidatePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(ISchemingDatasets)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "validate")

    # ISchemingDatasets

    def dataset_schema(self):
        return None

    def dataset_schemas(self):
        return ["ckanext.validate:schemas/dataset.yaml"]

