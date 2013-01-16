import logging
import requests
from flask import flash
from flask.ext import wtf
from flask.ext.admin import expose
from flask.ext.admin.babel import gettext

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



from rockpack.services.video import models as video_models

class VideoView(AdminView):
    model_name = 'video'
    model = video_models.Video

    create_template = 'admin/video/create.html'

    inline_models = (video_models.VideoThumbnail, )


    """def create_model(self, form):
        import pdb; pdb.set_trace()
        try:
            model = self.model()
            # TODO: HACK - harcocde the source for now (youtube)
            model.source = 1
            form.populate_obj(model)
            self.session.add(model)
            self.on_model_change(form, model)
            self._update_youtube_data(model)
            # add thumbnails
            self.session.commit()
            return True
        except Exception as e:
            flash(gettext('Failed to create model. %(error)s', error=str(e)), 'error')
            logging.exception('Failed to create model')
            self.session.rollback()
            return False"""
