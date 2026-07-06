import json

from flask import Blueprint

from ckan.lib import base
from ckan.plugins import toolkit

from ckanext.validate import helpers as h


validation_configuration_blueprint = Blueprint(
    "validate_configuration_admin",
    __name__,
)


def _get_admin_context():
    """Return the current CKAN context and ensure sysadmin access."""
    context = {
        "user": toolkit.current_user.name,
        "auth_user_obj": toolkit.current_user,
    }

    try:
        toolkit.check_access(
            "sysadmin",
            context,
        )
    except toolkit.NotAuthorized:
        base.abort(
            403,
            toolkit._(
                "Need to be system administrator to administer"
            ),
        )

    return context


def _configuration_form_data(configuration=None):
    """Return values used to populate the create/edit form."""
    schema = {
        "fields": [],
        "_validate_rules": [],
    }

    if configuration is None:
        return {
            "name": "",
            "description": "",
            "schema": json.dumps(
                schema,
                indent=2,
                ensure_ascii=False,
            ),
            "active": True,
        }

    return {
        "name": configuration.get("name") or "",
        "description": configuration.get("description") or "",
        "schema": json.dumps(
            configuration.get("schema") or schema,
            indent=2,
            ensure_ascii=False,
        ),
        "active": configuration.get("active", True),
    }


def _submitted_form_data():
    """Preserve submitted values after a validation error."""
    form = toolkit.request.form

    return {
        "name": form.get("name", "").strip(),
        "description": form.get("description", "").strip(),
        "schema": form.get("schema", "").strip(),
        "active": "active" in form,
    }


def _list_configurations(context):
    """Return all validation configurations through the CKAN action."""
    return toolkit.get_action(
        "validation_configuration_list"
    )(
        context,
        {},
    )


@validation_configuration_blueprint.route(
    "/ckan-admin/validation-configurations",
    methods=["GET", "POST"],
)
def validation_configurations():
    """List configurations and create a new configuration."""
    context = _get_admin_context()
    form_data = _configuration_form_data()

    if toolkit.request.method == "POST":
        form_data = _submitted_form_data()

        try:
            toolkit.get_action(
                "validation_configuration_create"
            )(
                context,
                form_data,
            )
        except toolkit.ValidationError as error:
            toolkit.h.flash_error(
                h.validation_error_message(error)
            )
        else:
            toolkit.h.flash_notice(
                toolkit._(
                    "Validation configuration created successfully."
                )
            )

            return toolkit.redirect_to(
                "validate_configuration_admin"
                ".validation_configurations"
            )

    return base.render(
        "admin/validation_configurations.html",
        extra_vars={
            "configurations": _list_configurations(context),
            "form_data": form_data,
            "selected_configuration_id": None,
        },
    )


@validation_configuration_blueprint.route(
    "/ckan-admin/validation-configurations/"
    "<configuration_id>/edit",
    methods=["GET", "POST"],
)
def validation_configuration_edit(configuration_id):
    """Edit an existing validation configuration."""
    context = _get_admin_context()

    try:
        configuration = toolkit.get_action(
            "validation_configuration_show"
        )(
            context,
            {
                "id": configuration_id,
            },
        )
    except toolkit.ObjectNotFound:
        base.abort(
            404,
            toolkit._(
                "Validation configuration not found."
            ),
        )

    form_data = _configuration_form_data(configuration)

    if toolkit.request.method == "POST":
        form_data = _submitted_form_data()

        try:
            toolkit.get_action(
                "validation_configuration_update"
            )(
                context,
                {
                    "id": configuration_id,
                    **form_data,
                },
            )
        except toolkit.ValidationError as error:
            toolkit.h.flash_error(
                h.validation_error_message(error)
            )
        else:
            toolkit.h.flash_notice(
                toolkit._(
                    "Validation configuration updated successfully."
                )
            )

            return toolkit.redirect_to(
                "validate_configuration_admin"
                ".validation_configuration_edit",
                configuration_id=configuration_id,
            )

    return base.render(
        "admin/validation_configuration_edit.html",
        extra_vars={
            "configuration": configuration,
            "configurations": _list_configurations(context),
            "form_data": form_data,
            "selected_configuration_id": configuration_id,
        },
    )


@validation_configuration_blueprint.route(
    "/ckan-admin/validation-configurations/"
    "<configuration_id>/delete",
    methods=["POST"],
)
def validation_configuration_delete(configuration_id):
    """Delete a validation configuration through the CKAN action."""
    context = _get_admin_context()

    try:
        configuration = toolkit.get_action(
            "validation_configuration_delete"
        )(
            context,
            {
                "id": configuration_id,
            },
        )
    except toolkit.ObjectNotFound:
        base.abort(
            404,
            toolkit._(
                "Validation configuration not found."
            ),
        )

    toolkit.h.flash_notice(
        toolkit._(
            'Validation configuration "{0}" deleted.'
        ).format(configuration["name"])
    )

    return toolkit.redirect_to(
        "validate_configuration_admin"
        ".validation_configurations"
    )
