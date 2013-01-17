import logging
from flask.ext import wtf
from flask import request
from flask.ext import login
from flask.ext.admin import BaseView, expose
from rockpack.mainsite.auth import models
from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.core.dbapi import session
from rockpack.mainsite.core.youtube import get_playlist_data
from rockpack.mainsite.services.video.models import Locale, Source, Category, ParentCategory


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


class UserView(AdminView):
    model = models.User
    model_name = models.User.__tablename__


class ImportForm(wtf.Form):
    source = wtf.SelectField(coerce=int, validators=[wtf.validators.required()])
    type = wtf.SelectField(choices=(('video', 'Video'), ('user', 'User'), ('playlist', 'Playlist')),
                           validators=[wtf.validators.required()])
    id = wtf.TextField(validators=[wtf.validators.required()])
    locale = wtf.SelectField(default='en-gb')
    category = wtf.SelectField(coerce=int)

    def validate(self):
        if not super(ImportForm, self).validate():
            return
        if self.source.data == 1:   # youtube
            if self.type.data == 'playlist':
                try:
                    self.import_data = get_playlist_data(self.id.data)
                except Exception, ex:
                    logging.exception('Unable to import playlist: %s', self.id.data)
                    self._errors = {'__all__': str(ex)}
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
        data = request.args.copy()
        source_choices = session.query(Source.id, Source.label)

        # Ugly reverse mapping of source labels
        source = data.get('source')
        if source:
            for id, label in source_choices:
                if source == label:
                    data['source'] = id

        form = ImportForm(data, csrf_enabled=False)
        form.source.choices = source_choices
        form.locale.choices = session.query(Locale.id, Locale.name)
        form.category.choices = [
            (id, '%s - %s' % (parent, name))
                for id, name, parent in session.
                    query(Category.id, Category.name, ParentCategory.name).
                    filter(Category.parent == ParentCategory.id).
                    filter(Category.locale == 'en-gb')]

        ctx['form'] = form
        if 'source' in data and form.validate():
            ctx['import_preview'] = form.import_data

        return self.render('admin/import.html', **ctx)

    @expose('/bookmarklet.js')
    def bookmarklet(self):
        return self.render('admin/import_bookmarklet.js')
