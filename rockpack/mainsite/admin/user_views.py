import wtforms as wtf
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

    form_excluded_columns = ('channels', 'flags', 'activity', 'external_friends')
    form_args = dict(
        username=dict(validators=[wtf.validators.Regexp('^\w{3,50}$', message='alphanumeric only')]),
        first_name=dict(validators=[wtf.validators.Optional()]),
        last_name=dict(validators=[wtf.validators.Optional()]),
        password_hash=dict(validators=[wtf.validators.Optional()]),
        email=dict(validators=[wtf.validators.Optional()]),
        date_of_birth=dict(validators=[wtf.validators.Optional()]),
        refresh_token=dict(validators=[wtf.validators.Optional()]),
        date_joined=dict(validators=[wtf.validators.Optional()]),
        date_updated=dict(validators=[wtf.validators.Optional()]),
    )

    inline_models = (auth_models.ExternalToken,)


class ExternalTokenView(AdminView):
    model = auth_models.ExternalToken
    model_name = model.__tablename__

    column_list = ('user_rel', 'external_system', 'external_uid')
    #column_filters = ('external_system',)
    column_searchable_list = (models.User.username, 'external_uid')

    form_ajax_refs = dict(
        user_rel={'fields': (models.User.username,)},
    )


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

    form_excluded_columns = ('date_created', 'date_processed')
    form_args = dict(
        filter=dict(validators=[_filter_validator]),
        url_target=dict(validators=[_url_target_validator]),
    )
