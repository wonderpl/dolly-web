from flask.ext.admin import Admin

import views
import video_views


def setup_admin(app):
    admin = Admin(app, endpoint='admin', name='Rockpack Admin')

    # video
    for v in video_views.admin_views():
        admin.add_view(v)

    # auth
    admin.add_view(views.UserView(
        name='User',
        endpoint='user',))

    """ TODO: add these back in later
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
    admin.add_view(views.UserRoleView(
        name='UserRoles',
        endpoint='permissions/user-permissions',
        category='Permissions'))
    """

    admin.add_view(views.ImportView(name='Import'))
