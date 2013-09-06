from flask.ext import wtf
from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.services.user import models
from rockpack.mainsite.services.oauth import models as auth_models


class UserView(AdminView):
    model = models.User
    model_name = models.User.__tablename__

    column_list = ('username', 'display_name', 'avatar.url', 'date_joined')
    column_filters = ('username', 'email', 'date_joined', 'is_active')
    column_searchable_list = ('username', )

    edit_template = 'admin/edit_with_child_links.html'
    child_links = (('Channels', 'channel', None),)

    form_args = dict(
        username=dict(validators=[wtf.Regexp('^\w{3,50}$', message='alphanumeric only')]),
        last_name=dict(validators=[wtf.Optional()]),
        password_hash=dict(validators=[wtf.Optional()]),
        email=dict(validators=[wtf.Optional()]),
        date_of_birth=dict(validators=[wtf.Optional()]),
        refresh_token=dict(validators=[wtf.Optional()]),
        date_joined=dict(validators=[wtf.Optional()]),
        date_updated=dict(validators=[wtf.Optional()]),
    )

    inline_models = (auth_models.ExternalToken,)


class ExternalTokenView(AdminView):
    model = auth_models.ExternalToken
    model_name = model.__tablename__

    column_list = ('user_rel', 'external_system', 'external_uid')
    #column_filters = ('external_system',)
    column_searchable_list = (models.User.username, 'external_uid')

    form_overrides = dict(user_rel=wtf.TextField)


def _filter_validator(form, field):
    if field.data:
        for expr, type, values in models.BroadcastMessage.parse_filter_string(field.data):
            if type is None:
                raise wtf.ValidationError('Invalid filter expression: %s' % expr)


def _url_target_validator(form, field):
    if field.data:
        if not models.BroadcastMessage.get_target_resource_url(field.data):
            raise wtf.ValidationError('Invalid target id')


class BroadcastMessageView(AdminView):
    model = models.BroadcastMessage
    model_name = model.__tablename__

    column_list = ('label', 'external_system', 'date_scheduled', 'date_processed')
    column_filters = ('date_scheduled',)
    column_searchable_list = ('label',)

    form_columns = ('label', 'external_system', 'date_scheduled', 'message', 'url_target', 'filter')
    form_args = dict(
        filter=dict(validators=[_filter_validator]),
        url_target=dict(validators=[_url_target_validator]),
    )
