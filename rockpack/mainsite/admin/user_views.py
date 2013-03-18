from flask.ext import wtf
from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.services.user import models


class UserView(AdminView):
    model = models.User
    model_name = models.User.__tablename__

    column_list = ('username', 'email', 'avatar.thumbnail_medium')
    column_filters = ('username', 'email',)

    edit_template = 'admin/edit_with_child_links.html'
    child_links = (('Channels', 'channel', 'username'),)

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
