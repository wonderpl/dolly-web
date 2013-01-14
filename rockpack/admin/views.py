from flask import flash
from flask.ext.admin import BaseView
from flask.ext.admin import expose
from flask.ext import wtf
from flask.ext.admin.model import BaseModelView
from flask import Response
from flask import redirect
from flask import url_for
from flask import session as flask_session

from sqlalchemy.sql.expression import desc

from rockpack.auth import models
from rockpack.auth import google
from rockpack.core.dbapi import session

class AdminView(BaseView):
    @expose('/')
    def index(self):
        import pdb;pdb.set_trace()
        access_token = flask_session.get('access_token')
        if access_token is None:
            return redirect(url_for('login'))

        userinfo = google.get('userinfo', access_token=access_token)
        return Response(userinfo.content, mimetype='text/plain')

class PermissionHomeView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/index.html')

class RoleForm(wtf.Form):
    name = wtf.TextField()

class RoleView(BaseModelView):

    model = models.Role

    def __init__(self, *args, **kwargs):
        super(RoleView, self).__init__(self.model, *args, **kwargs)

    @property
    def can_delete(self):
        # if login.current_user.is_authenticated
        #   and self.current_user.has_permission(self.__class__.__name__ + '_delete'):
        #   return True
        return False

    def get_pk_value(self, model):
        return self.model.id

    def scaffold_filters(self):
        return None

    def scaffold_list_columns(self):
        return ['name']

    def scaffold_sortable_columns(self):
        return {'name': self.model.name}

    def scaffold_form(self):
        return RoleForm

    def get_list(self, page, sort_field, sort_desc, search, filters):
        query = session.query(self.model)

        # do filtering

        count = query.count()

        if sort_desc:
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)

        if page:
            query = query.offset(page * self.page_size)

        query = query.limit(self.page_size)

        result = query.all()

        return count, result

    def get_one(self, id):
        return session.query(self.model).get(id)

    def create_model(self, form):
        try:
            model = self.model()
            form.populate_obj(model)
            session.add(model)
            session.commit()
            return True
        except Exception as e:
            flash('Failed to create entry. {}'.format(e))
            return False


class PermissionView(BaseView):
    @expose('/')
    def roles(self):
        return self.render('admin/index.html')


class RolePermissionView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/index.html')


class UserRoleView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/index.html')
