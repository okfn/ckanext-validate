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
    """Only sysadmins can see the validation job status."""
    return toolkit.check_access("sysadmin", context, data_dict)


def validate_test_file(context, data_dict):
    """Allow sysadmins and organization editors/admins to validate test files."""
    current_user = context.get("auth_user_obj")
    username = context.get("user")

    if getattr(current_user, "sysadmin", False):
        return {"success": True}

    if not username:
        return {
            "success": False,
            "msg": toolkit._(
                "You must be logged in to validate a file."
            ),
        }

    organizations = toolkit.get_action(
        "organization_list_for_user"
    )(
        {
            "user": username,
            "auth_user_obj": current_user,
        },
        {
            "id": username,
            "permission": "create_dataset",
            "include_dataset_count": False,
        },
    )

    if organizations:
        return {"success": True}

    return {
        "success": False,
        "msg": toolkit._(
            "You must be an editor or administrator to validate a file."
        ),
    }
