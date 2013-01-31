from flask.ext import login, wtf
from flask.ext.admin.model.typefmt import BASE_FORMATTERS, Markup
from flask.ext.admin.model.form import converts
from flask.ext.admin.contrib.sqlamodel import ModelView, form, filters
from rockpack.mainsite.helpers.db import ImageUrl
from rockpack.mainsite.core.dbapi import db


def _render_image(img):
    # TODO: specify image width & height?
    return Markup('<img src="%s"/>' % img)


class AdminModelConverter(form.AdminModelConverter):
    @converts('ImageType')
    def conv_ImagePath(self, field_args, **extra):
        # XXX: Allow form to be edited without replacing existing image
        # There must be a better way to do this!
        field_args['validators'] = [v for v in field_args['validators']
                                    if not isinstance(v, wtf.validators.Required)]
        return wtf.FileField(**field_args)


class AdminFilterConverter(filters.FilterConverter):
    @filters.filters.convert('CHAR')
    def conv_char(self, column, name):
        return [f(column, name) for f in self.strings]


class AdminView(ModelView):

    model_name = None
    model = None

    can_create = True
    can_edit = True
    can_delete = False

    column_type_formatters = dict({ImageUrl: _render_image}, **BASE_FORMATTERS)
    model_form_converter = AdminModelConverter
    filter_converter = AdminFilterConverter()

    def __init__(self, *args, **kwargs):
        super(AdminView, self).__init__(self.model, db.session, **kwargs)

    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()

    def update_model(self, form, model):
        # XXX: Allow form to be edited without replacing existing image
        # There must be a better way to do this!
        for field in form:
            if isinstance(field, wtf.FileField) and not field.data:
                form._fields.pop(field.name)
        return super(AdminView, self).update_model(form, model)


# TODO: implement the below - ignoring for now, just let people sign in.
# allow everything else
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
        # and self.current_user.has_permission(self.__class__.__name__ + '_delete'):
        # return True
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
