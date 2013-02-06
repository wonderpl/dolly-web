from rockpack.mainsite.auth import models
from rockpack.mainsite.admin.models import AdminView


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


class AdminView(AdminView):
    model = models.Admin
    model_name = models.Admin.__tablename__


class UserView(AdminView):
    model = models.User
    model_name = models.User.__tablename__

    column_list = ('username', 'email', 'avatar.thumbnail_medium')
    column_filters = ('username', 'email',)

    edit_template = 'admin/edit_with_child_links.html'
    child_links = (('Channels', 'channel', 'username'),)
