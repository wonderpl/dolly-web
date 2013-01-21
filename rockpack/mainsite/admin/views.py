import logging
from flask import request, url_for, redirect, flash
from flask.ext import wtf, login
from flask.ext.admin import BaseView, expose
from rockpack.mainsite.auth import models
from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.core import youtube
from rockpack.mainsite.services.video.models import Locale, Source, Category, Video


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


class ImportForm(wtf.Form):
    source = wtf.SelectField(coerce=int, validators=[wtf.validators.required()])
    type = wtf.SelectField(choices=(('video', 'Video'), ('admin', 'Admin'), ('playlist', 'Playlist')),
                           validators=[wtf.validators.required()])
    id = wtf.TextField(validators=[wtf.validators.required()])
    locale = wtf.SelectField(default='en-gb')
    category = wtf.SelectField(coerce=int, default=-1)
    commit = wtf.HiddenField()

    def validate(self):
        if not super(ImportForm, self).validate():
            return
        if self.commit.data and self.category.data == -1:
            # category is required before commit
            self.category.errors = ['Please select a category']
            return
        if self.source.data == 1:   # youtube
            get_data = getattr(youtube, 'get_%s_data' % self.type.data)
            try:
                # get all data only if we are ready to commit
                self.import_data = get_data(self.id.data, self.commit.data)
            except Exception, ex:
                logging.exception('Unable to import %s: %s', self.type.data, self.id.data)
                self._errors = {'__all__': 'Internal error: %r' % ex}
            else:
                return True


class ImportView(BaseView):

    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()

    @expose('/', ('GET', 'POST'))
    def index(self):
        ctx = {}
        data = (request.form or request.args).copy()
        source_choices = Source.get_form_choices()

        # Ugly reverse mapping of source labels
        source = data.get('source')
        if source:
            for id, label in source_choices:
                if source == label:
                    data['source'] = id

        form = ImportForm(data, csrf_enabled=False)
        form.source.choices = source_choices
        form.locale.choices = Locale.get_form_choices()
        form.category.choices = [(-1, '')] +\
            list(Category.get_form_choices(form.locale.data))

        ctx['form'] = form
        if 'source' in data and form.validate():
            if form.commit.data:
                count = Video.add_videos(
                    form.import_data.videos,
                    form.source.data,
                    form.locale.data,
                    form.category.data)
                flash('Imported %d videos' % count)
                return redirect(url_for('video.index_view'))
            else:
                ctx['import_preview'] = form.import_data
                form.commit.data = 'true'

        return self.render('admin/import.html', **ctx)

    @expose('/bookmarklet.js')
    def bookmarklet(self):
        return self.render('admin/import_bookmarklet.js')
