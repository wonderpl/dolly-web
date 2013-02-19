from flask import redirect, url_for, session, current_app, make_response
from flask.ext.login import login_user, logout_user
from ..models import AdminView
from .user import User
from . import models, google_oauth


def login():
    return google_oauth.authorize(callback=url_for('.oauth_callback', _external=True),
                                  scope='https://www.googleapis.com/auth/userinfo.email')


def logout():
    logout_user()

    # remove any keys
    if session.get('access_token'):
        session.pop('access_token')

    response = make_response(redirect(url_for('admin.index')))
    response.delete_cookie('access_token')
    return response


@google_oauth.authorized_handler()
def oauth_callback(response, access_token):
    if response == 'access denied' or not access_token:
        return 'Not logging in with Google account' +\
               '<a href="{}">Login again</a>'.format(url_for('.login'))

    current_app.logger.debug('loggin in .... checking token')
    user = User.get_from_token(access_token)
    if not user:
        current_app.logger.debug('no token found, cross-referencing email against token')
        response = google_oauth.get('https://www.googleapis.com/oauth2/v1/userinfo?alt=json', access_token=access_token).response
        if response.status_code != 200:
            current_app.logger.error('Failed to retrieve userinfo with: {}'.format(response.content))
            return 'Error fetching userinfo', 500
        email = response.json().get('email')
        user = User.register_token(access_token, email)
        if not user:
            return 'No registered email address found', 401

    login_user(user, remember=True)
    session['access_token'] = access_token

    # else redirect them to failed login page
    return redirect(url_for('admin.index'))


class RoleView(AdminView):
    model_name = 'role'
    model = models.Role


class RolePermissionView(AdminView):
    model_name = 'role_permission'
    model = models.RolePermissions


class PermissionView(AdminView):
    model_name = 'permission'
    model = models.Permission


class AdminRoleView(AdminView):
    model_name = 'admin_role'
    model = models.AdminRole


class AdminUserView(AdminView):
    model = models.AdminUser
    model_name = models.AdminUser.__tablename__
