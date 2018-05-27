import jwt
from flask import request
from flask_babel import _, lazy_gettext as _l
import appkernel
from appkernel.configuration import config


def check_token(jwt_token):
    return jwt.decode(jwt_token, config.public_key)


def authorize_request():
    def contains_denied():
        denied_permissions = [permission for permission in required_permissions if
                              isinstance(permission, appkernel.Denied)]
        return len(denied_permissions) > 0

    required_permissions = config.service_registry.get(request.endpoint).get_required_permission(request.method,
                                                                                                 request.endpoint)
    if required_permissions:
        if isinstance(required_permissions, appkernel.Permission):
            required_permissions = [required_permissions]
        elif not isinstance(required_permissions, list):
            return appkernel.Service.app_engine.create_custom_error(401, _(
                'The permission type {} is not supported.'.format(required_permissions.__class__.__name__)))

        if contains_denied():
            return appkernel.Service.app_engine.create_custom_error(403, _('Not allowed to access method.'))

        authorisation_header = request.headers.get('Authorization')
        if not authorisation_header:
            return appkernel.Service.app_engine.create_custom_error(401, _('The authorisation header is missing.'))
        try:
            missing_required_role = True
            missing_required_authority = True

            token = check_token(authorisation_header.split(' ')[1])

            required_roles = set()
            required_authorities = set()
            for item in required_permissions:
                if isinstance(item, appkernel.Role):
                    required_roles.add(item.name)
                elif isinstance(item, appkernel.Authority):
                    required_authorities.add(item)

            if len(required_roles.intersection(set(token.get('roles', [])))) > 0:
                missing_required_role = False

            if missing_required_role and missing_required_authority:
                return appkernel.Service.app_engine.create_custom_error(403, _(
                    'The required permission is missing.'))
        except Exception as exc:
            return appkernel.Service.app_engine.create_custom_error(403, str(exc))
