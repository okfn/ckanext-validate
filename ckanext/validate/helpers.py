from ckanext.validate.model.validation import Validation


def get_resource_validation_state(resource_dict):
    if not resource_dict:
        return None

    status = Validation.get_resource_status(resource_dict.get("id"))
    if status:
        return status

    return None
