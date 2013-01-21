from flask.ext.admin import Admin

import views
import video_views


def setup_admin(app):
    admin = Admin(app, endpoint='admin', name='Rockpack Admin')

    # video
    for v in video_views.admin_views():
        admin.add_view(v)

    # auth
    admin.add_view(views.AdminView(
        name='Admin Users',
        endpoint='admin-user',))

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
    admin.add_view(views.AdminRoleView(
        name='AdminRoles',
        endpoint='permissions/admin-permissions',
        category='Permissions'))
    """

    admin.add_view(views.ImportView(name='Import', endpoint='import'))
