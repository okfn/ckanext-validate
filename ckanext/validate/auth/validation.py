from ckan.plugins import toolkit


def resource_validate(context, data_dict):
    """Only users who can update a resource can trigger validation."""
    try:
        toolkit.check_access("resource_update", context, data_dict)
    except toolkit.NotAuthorized:
        return {"success": False, "msg": toolkit._("Not authorized to validate this resource")}
    return {"success": True}


def resource_validation_show(context, data_dict):
    """Anyone who can view a resource can see its validation results."""
    try:
        toolkit.check_access("resource_show", context, data_dict)
    except toolkit.NotAuthorized:
        return {"success": False, "msg": toolkit._("Not authorized to view this resource")}
    return {"success": True}


def validation_job_list(context, data_dict):
    """Only sysadmins can list validation jobs."""
    return toolkit.check_access("sysadmin", context, data_dict)


def resource_validation_status(context, data_dict):
    """Anyone who can view a resource can see its validation status."""
    try:
        toolkit.check_access("resource_show", context, data_dict)
    except toolkit.NotAuthorized:
        return {
            "success": False, 
            "msg": toolkit._("Not authorized to view this resource")
        }
    return {"success": True}
