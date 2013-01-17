from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqlamodel import ModelView

from rockpack.mainsite.core.dbapi import session
from rockpack.mainsite.services.video import models as video_models
from rockpack.mainsite import auth
import views

def setup_admin(app):
    admin = Admin(app, endpoint='admin', name='Rockpack Admin')
    admin.add_view(ModelView(video_models.VideoInstance, session, category='Video'))
    admin.add_view(ModelView(video_models.VideoThumbnail, session, category='Video'))
    admin.add_view(ModelView(video_models.Source, session))
    admin.add_view(ModelView(video_models.Category, session))
    admin.add_view(ModelView(video_models.Locale, session))
    admin.add_view(ModelView(video_models.Channel, session))
    admin.add_view(ModelView(video_models.ExternalCategoryMap, session))

    admin.add_view(views.VideoView(name='Video', endpoint='video', category='Video'))

    # auth
    admin.add_view(ModelView(auth.models.User, session))

    admin.add_view(views.RoleView(name='Roles', endpoint='permissions/roles', category='Permissions'))
    admin.add_view(views.PermissionView(name='Permissions', endpoint='permissions/permissions', category='Permissions'))
    admin.add_view(views.RolePermissionView(name='RolePermissions', endpoint='permissions/role-permissions', category='Permissions'))
    admin.add_view(views.UserRoleView(name='UserRoles', endpoint='permissions/user-permissions', category='Permissions'))

    admin.add_view(views.ImportView(name='Import'))
