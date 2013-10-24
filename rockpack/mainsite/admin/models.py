from sqlalchemy import (
    String, Column, Integer, DateTime, Date, Enum, CHAR, func, PrimaryKeyConstraint)
from werkzeug import FileStorage
import wtforms as wtf
from flask.ext import login
from flask.ext.admin.model.typefmt import BASE_FORMATTERS, Markup
from flask.ext.admin.model.form import converts
from flask.ext.admin.contrib.sqla import ModelView, form, filters
from rockpack.mainsite.helpers.db import ImageUrl, ImageType, resize_and_upload, get_box_value
from rockpack.mainsite.helpers.http import get_external_resource
from rockpack.mainsite.core.dbapi import db


class AdminLogRecord(db.Model):

    __tablename__ = 'admin_log'

    id = Column(Integer(), primary_key=True)
    username = Column(String(254), nullable=False)
    timestamp = Column(DateTime(), nullable=False, default=func.now())
    action = Column(String(254), nullable=False)
    model = Column(String(254), nullable=False)
    instance_id = Column(String(254), nullable=False)
    value = Column(String(254), nullable=False)


class AppDownloadRecord(db.Model):
    __tablename__ = 'app_download'
    __table_args__ = (
        PrimaryKeyConstraint('source', 'version', 'action', 'country', 'date'),
    )

    source = Column(Enum('itunes', 'playstore', name='app_download_source'), nullable=False)
    version = Column(String(16), nullable=False)
    action = Column(Enum('download', 'update', name='app_download_action'), nullable=False)
    country = Column(CHAR(2), nullable=False)
    date = Column(Date(), nullable=False)
    count = Column(Integer(), nullable=False, server_default='0')


def _render_image(view, img=None):
    # TODO: specify image width & height?
    return Markup('<img src="%s"/>' % img)


def _box_validator(form, field):
    try:
        get_box_value(field.data)
    except (SyntaxError, AssertionError):
        raise wtf.ValidationError('Must be of the form: [x1, y1, x2, y2]')


class AdminModelConverter(form.AdminModelConverter):
    @converts('ImageType')
    def conv_ImagePath(self, field_args, **extra):
        # XXX: Allow form to be edited without replacing existing image
        # There must be a better way to do this!
        field_args['validators'] = [v for v in field_args['validators']
                                    if not isinstance(v, wtf.validators.InputRequired)]
        try:
            # Check for `reference_only` on the col type obj
            # and return a text field if true, else a file field
            for k, v in self.__dict__['view'].model.__table__.c.items():
                if isinstance(v.type, ImageType) and v.type.reference_only:
                    return wtf.TextField(**field_args)
        except:
            pass
        return wtf.FileField(**field_args)

    @converts('BoxType')
    def conv_BoxType(self, field_args, **extra):
        field_args['validators'].append(_box_validator)
        return wtf.TextField(**field_args)


class AdminFilterConverter(filters.FilterConverter):
    @filters.filters.convert('CHAR')
    def conv_char(self, column, name, **kwargs):
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

    def _process_image_data(self, form, model=None):
        for field in form:
            if isinstance(field, wtf.FileField):
                data = None
                cfgkey = self.model.__table__.columns.get(field.name).type.cfgkey
                aoi = form.data.get(field.name + '_aoi')
                if aoi:
                    aoi = get_box_value(aoi)
                if field.data:
                    # New image upload
                    data = field.data
                elif aoi and model and not getattr(model, field.name + '_aoi') == aoi:
                    # Same image, aoi updated - need to fetch the image data
                    data = getattr(model, field.name).original
                else:
                    # Allow form to be edited without replacing existing image
                    form._fields.pop(field.name)
                if data:
                    try:
                        if not isinstance(data, FileStorage):
                            data = get_external_resource(data)
                        field.data = resize_and_upload(data, cfgkey, aoi)
                    except IOError, e:
                        # The form has already been validated at this stage but
                        # if we return False then BaseModelView.create_view will
                        # still drop through and render the errors
                        field.errors = [getattr(e, 'message', str(e))]
                        return False
        return True

    def create_model(self, form):
        if self._process_image_data(form):
            # bad bad bad hack
            from rockpack.mainsite.services.user.models import User
            from rockpack.mainsite.services.video.models import Channel, Video
            for f in filter(lambda x: x.endswith('_rel'), form.data.keys()):
                if isinstance(getattr(form, f).data, unicode) or isinstance(getattr(form, f).data, str):
                    field = getattr(form, f)
                    if f == 'owner_rel':
                        model = User
                    if f == 'video_rel':
                        model = Video
                    if f == 'channel_rel':
                        model = Channel
                    field.data = model.query.get(getattr(form, f).data)
            return super(AdminView, self).create_model(form)

    def update_model(self, form, model):
        if self._process_image_data(form, model):
            # hack for owner_rel passing models around
            for f in filter(lambda x: x.endswith('_rel') or x == 'video_channel', form.data.keys()):
                if isinstance(getattr(form, f).data, unicode) or isinstance(getattr(form, f).data, str):
                    field = getattr(form, f)
                    field.data = getattr(model, f).query.get(getattr(form, f).data)
            return super(AdminView, self).update_model(form, model)

    def record_action(self, action, model):
        self.session.add(AdminLogRecord(
            username=login.current_user.username,
            action=action,
            model=model.__class__.__name__,
            instance_id=unicode(model.id),
            value=unicode(model),
        ))

    def on_model_change(self, form, model, is_created):
        self.record_action('created' if is_created else 'changed', model)

    def on_model_delete(self, model):
        self.record_action('deleted', model)


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
