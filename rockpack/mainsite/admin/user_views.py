import wtforms as wtf
from rockpack.mainsite.services.user import models
from rockpack.mainsite.services.oauth import models as auth_models
from rockpack.mainsite.services.cover_art import models as coverart_models
from .auth.models import AdminUser
from .base import AdminModelView


class AdminUserView(AdminModelView):
    model = AdminUser

    column_list = ('username', 'email')
    form_excluded_columns = ('adminrole',)


class UserView(AdminModelView):
    model = models.User

    column_list = ('username', 'display_name', 'avatar.url', 'date_joined')
    column_filters = ('username', 'email', 'date_joined', 'is_active')
    column_searchable_list = ('username', )

    edit_template = 'admin/edit_with_child_links.html'
    child_links = (('Channels', 'channel', None),)

    form_excluded_columns = ('channels', 'flags', 'activity', 'external_friends', 'user_promotion')
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


class UserCoverArtView(AdminModelView):
    model = coverart_models.UserCoverArt

    column_list = ('owner_rel', 'cover.url', 'date_created')
    column_filters = ('owner_rel',)

    form_ajax_refs = dict(
        owner_rel={'fields': (models.User.username,)},
    )

    edit_template = 'admin/cover_art_edit.html'
    create_template = 'admin/cover_art_create.html'

    def update_model(self, form, model):
        prev_cover = model.cover.path
        success = super(UserCoverArtView, self).update_model(form, model)
        if success and isinstance(form.cover.data, basestring):
            # Update channels that refer to this cover
            models.Channel.query.filter_by(owner=model.owner, cover=prev_cover).update(
                dict(cover=model.cover.path, cover_aoi=model.cover_aoi))
            self.session.commit()
        return success


class UserSubscriptionRecommendationView(AdminModelView):
    model = models.UserSubscriptionRecommendation

    column_list = ('user_rel', 'category_rel', 'priority')
    column_filters = ('category',)
    column_searchable_list = (models.User.username,)

    form_ajax_refs = dict(
        user_rel={'fields': (models.User.username,)},
    )


class ExternalTokenView(AdminModelView):
    model = auth_models.ExternalToken

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


class BroadcastMessageView(AdminModelView):
    model = models.BroadcastMessage

    column_list = ('label', 'external_system', 'date_scheduled', 'date_processed')
    column_filters = ('date_scheduled',)
    column_searchable_list = ('label',)

    form_excluded_columns = ('date_created', 'date_processed')
    form_args = dict(
        filter=dict(validators=[_filter_validator]),
        url_target=dict(validators=[_url_target_validator]),
    )
