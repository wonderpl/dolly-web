from flask import flash
from flask.ext import login
from flask.ext.admin import BaseView
from flask.ext.admin.model import BaseModelView
from sqlalchemy.sql.expression import desc
from flask.ext.admin.contrib.sqlamodel import ModelView

from rockpack.core.dbapi import session

class AdminView(ModelView):

    model_name = None
    model = None

    can_create = True
    can_edit   = True
    can_delete = True

    def __init__(self, *args, **kwargs):
        super(AdminView, self).__init__(self.model, session, **kwargs)

    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()

# TODO: implement the below - ignoring for now, just let people sign in. allow everything else
"""
    @property
    def can_create(self):
        permission = self.model_name.lower() + '_create'
        try:
            return login.current_user.has_permission(permission)
        except AttributeError:
            return False

    @property
    def can_edit(self):
        permission = self.model_name.lower() + '_edit'
        try:
            return login.current_user.has_permission(permission)
        except AttributeError:
            return False

    @property
    def can_delete(self):
        permission = self.model_name.lower() + '_delete'
        try:
            return login.current_user.has_permission(permission)
        except AttributeError:
            return False
"""

"""
class AdminModelView(BaseModelView, AdminView):

    model = None
    form  = None

    list_columns = []
    sortable_columns = []
    filters = []

    def __init__(self, *args, **kwargs):
        super(AdminModelView, self).__init__(self.model, *args, **kwargs)

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
        return self.form

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
"""
