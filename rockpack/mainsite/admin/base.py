import re
import wtforms as wtf
from werkzeug import FileStorage
from flask.ext import login
from flask.ext.admin import BaseView
from flask.ext.admin.model.form import converts
from flask.ext.admin.model.typefmt import Markup, BASE_FORMATTERS
from flask.ext.admin.contrib.sqla import ModelView, form, filters
from rockpack.mainsite.helpers.db import ImageUrl, ImageType, resize_and_upload, get_box_value
from rockpack.mainsite.helpers.http import get_external_resource
from rockpack.mainsite.core.dbapi import db
from .models import AdminLogRecord


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


class AuthMixin(object):

    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()


class AdminView(BaseView, AuthMixin):
    pass


class AdminModelView(ModelView, AuthMixin):

    model = None

    can_create = True
    can_edit = True
    can_delete = False

    column_type_formatters = dict({ImageUrl: _render_image}, **BASE_FORMATTERS)
    model_form_converter = AdminModelConverter
    filter_converter = AdminFilterConverter()

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('endpoint', self.model.__tablename__)
        super(AdminModelView, self).__init__(self.model, db.session, **kwargs)

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
            return super(AdminModelView, self).create_model(form)

    def update_model(self, form, model):
        if self._process_image_data(form, model):
            # hack for owner_rel passing models around
            for f in filter(lambda x: x.endswith('_rel') or x == 'video_channel', form.data.keys()):
                if isinstance(getattr(form, f).data, unicode) or isinstance(getattr(form, f).data, str):
                    field = getattr(form, f)
                    field.data = getattr(model, f).query.get(getattr(form, f).data)
            return super(AdminModelView, self).update_model(form, model)

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

    def prettify_name(self, name):
        # Split class names on capitalised word:
        name = re.sub('\B[A-Z]', ' \\g<0>', name)
        return super(AdminModelView, self).prettify_name(name)
