from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqlamodel import ModelView

from rockpack.core.dbapi import session
from rockpack.services.video import models
from views import PermissionView

def setup_admin(app):
    admin = Admin(app, endpoint='admin', name='Rockpack Admin')
    admin.add_view(ModelView(models.Video, session))
    admin.add_view(ModelView(models.VideoInstance, session))
    admin.add_view(ModelView(models.VideoSource, session))
    admin.add_view(ModelView(models.Category, session))
    admin.add_view(ModelView(models.Locale, session))
    admin.add_view(ModelView(models.Channel, session))

    admin.add_view(PermissionView(name='Roles', endpoint='a/roles', category='Permissions'))
    admin.add_view(PermissionView(name='Needs', endpoint='a/needs', category='Permissions'))
    admin.add_view(PermissionView(name='Access Rights', endpoint='a/access_rights', category='Permissions'))
