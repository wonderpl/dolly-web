from flask.ext import wtf
from flask import request
from flask.ext import login
from flask.ext.admin import BaseView, expose
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


class ImportView(BaseView):

    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()

    @expose('/', ('GET', 'POST'))
    def index(self):
        ctx = {}
        data = request.args.copy()
        source_choices = ((1, 'youtube'),)  # TODO: select from db

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
