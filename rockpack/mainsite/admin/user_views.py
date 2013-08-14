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
