import logging
import requests
from flask import flash
from flask.ext import wtf
from flask import request
from flask.ext.admin import BaseView, expose
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


class ImportForm(wtf.Form):
    source = wtf.SelectField(coerce=int, validators=[wtf.validators.required()])
    type = wtf.SelectField(choices=(('video', 'Video'), ('user', 'User'), ('playlist', 'Playlist')), validators=[wtf.validators.required()])
    id = wtf.TextField(validators=[wtf.validators.required()])


class ImportView(BaseView):

    @expose('/', ('GET', 'POST'))
    def index(self):
        ctx = {}
        data = request.args.copy()
        source_choices = ((1, 'youtube'),) # TODO: select from db

        # Ugly reverse mapping of source labels
        source = data.get('source')
        if source:
            for id, label in source_choices:
                if source == label:
                    data['source'] = id

        form = ImportForm(data, csrf_enabled=False)
        form.source.choices = source_choices

        if data and form.validate():
            ctx.update(form.data)
        else:
            ctx['form'] = form

        return self.render('admin/import.html', **ctx)

    @expose('/bookmarklet.js')
    def bookmarklet(self):
        return self.render('admin/import_bookmarklet.js')
