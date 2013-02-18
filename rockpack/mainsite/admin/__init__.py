from flask.ext.admin import Admin
from . import video_views, import_views, user_views


def setup_admin(app):
    admin = Admin(app, endpoint='admin', name='Rockpack Admin')

    # video
    for v in video_views.admin_views():
        admin.add_view(v)

    # Need to import here to avoid import uninitialised google_oauth decorator
    from .auth.views import login, logout, oauth_callback
    for view in login, logout, oauth_callback:
        app.add_url_rule('%s/%s' % (admin.url, view.func_name), view.func_name, view)

    """ TODO: add these back in later
    admin.add_view(views.AdminView(
        name='Admin Users',
        endpoint='admin-user'))
    admin.add_view(views.RoleView(
        name='Roles',
        endpoint='permissions/roles',
        category='Permissions'))
    admin.add_view(views.PermissionView(
        name='Permissions',
        endpoint='permissions/permissions',
        category='Permissions'))
    admin.add_view(views.RolePermissionView(
        name='RolePermissions',
        endpoint='permissions/role-permissions',
        category='Permissions'))
    admin.add_view(views.AdminRoleView(
        name='AdminRoles',
        endpoint='permissions/admin-permissions',
        category='Permissions'))
    """

    admin.add_view(user_views.UserView(name='Users', endpoint='user'))
    admin.add_view(import_views.ImportView(name='Import', endpoint='import'))
