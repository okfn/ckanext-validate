from ckan import model
from ckan.plugins import toolkit


def _get_resource(resource_id):
    return model.Resource.get(resource_id)


def resource_validate(context, data_dict):
    """Only users who can update a resource can trigger validation."""
    resource_id = data_dict.get("id")
    if not resource_id:
        return {"success": False, "msg": toolkit._("No resource id provided")}
    resource = _get_resource(resource_id)
    if not resource:
        return {"success": False, "msg": toolkit._("Resource not found")}
    return toolkit.check_access(
        "resource_update", context, {"id": resource_id}
    ) or {"success": True}


def resource_validation_show(context, data_dict):
    """Anyone who can view a resource can see its validation results."""
    resource_id = data_dict.get("id")
    if not resource_id:
        return {"success": False, "msg": toolkit._("No resource id provided")}
    resource = _get_resource(resource_id)
    if not resource:
        return {"success": False, "msg": toolkit._("Resource not found")}
    return {"success": True}
