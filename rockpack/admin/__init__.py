from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqlamodel import ModelView

from rockpack.core.dbapi import session
from rockpack.services.video import models as video_models
from rockpack import auth
import views

def setup_admin(app):
    admin = Admin(app, endpoint='admin', name='Rockpack Admin')
    admin.add_view(ModelView(video_models.Video, session))
    admin.add_view(ModelView(video_models.VideoInstance, session))
    admin.add_view(ModelView(video_models.VideoSource, session))
    admin.add_view(ModelView(video_models.Category, session))
    admin.add_view(ModelView(video_models.Locale, session))
    admin.add_view(ModelView(video_models.Channel, session))

    # auth
    admin.add_view(ModelView(auth.models.User, session))

    admin.add_view(views.RoleView(name='Roles', endpoint='permissions/roles', category='Permissions'))
    admin.add_view(views.PermissionView(name='Permissions', endpoint='permissions/permissions', category='Permissions'))
    admin.add_view(views.RolePermissionView(name='RolePermissions', endpoint='permissions/role-permissions', category='Permissions'))
    admin.add_view(views.UserRoleView(name='UserRoles', endpoint='permissions/user-permissions', category='Permissions'))
