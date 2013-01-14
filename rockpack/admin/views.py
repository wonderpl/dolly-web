from flask.ext import wtf
from flask.ext.admin import expose

from rockpack.auth import models
from rockpack.admin.models import AdminView
#from rockpack.admin.models import AdminModelView


# Roles

class RoleView(AdminView):
    model_name = 'role'
    model = models.Role

class RolePermissionView(AdminView):
    model_name = 'role_permission'
    model = models.RolePermissions

class PermissionView(AdminView):
    model_name = 'permission'
    model = models.Permission

class UserRoleView(AdminView):
    model_name = 'user_role'
    model = models.UserRole
