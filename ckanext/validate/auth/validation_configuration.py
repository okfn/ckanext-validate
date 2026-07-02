from ckan.plugins import toolkit


def validation_configuration_create(context, data_dict):
    """Only sysadmins can create validation configurations."""
    return toolkit.check_access(
        "sysadmin",
        context,
        data_dict,
    )


def validation_configuration_show(context, data_dict):
    """Only sysadmins can inspect validation configurations."""
    return toolkit.check_access(
        "sysadmin",
        context,
        data_dict,
    )


def validation_configuration_list(context, data_dict):
    """Only sysadmins can list validation configurations."""
    return toolkit.check_access(
        "sysadmin",
        context,
        data_dict,
    )


def validation_configuration_update(context, data_dict):
    """Only sysadmins can update validation configurations."""
    return toolkit.check_access(
        "sysadmin",
        context,
        data_dict,
    )


def validation_configuration_delete(context, data_dict):
    """Only sysadmins can delete validation configurations."""
    return toolkit.check_access(
        "sysadmin",
        context,
        data_dict,
    )
