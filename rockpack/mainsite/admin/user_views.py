import wtforms as wtf
from flask import request, url_for, redirect, flash, json, jsonify
from flask.ext.admin import expose
from rockpack.mainsite import app
from rockpack.mainsite.services.user import models
from rockpack.mainsite.services.oauth import models as auth_models
from rockpack.mainsite.services.cover_art import models as coverart_models
from rockpack.mainsite.services.video import models as video_models
from .auth.models import AdminUser
from .base import AdminModelView
import twitter


class AdminUserView(AdminModelView):
    model = AdminUser

    column_list = ('username', 'email')
    form_excluded_columns = ('adminrole',)


class UserView(AdminModelView):
    model = models.User

    column_list = ('username', 'display_name', 'avatar.url', 'date_joined')
    column_filters = ('username', 'email', 'date_joined', 'is_active')
    column_searchable_list = ('username', )

    edit_template = 'admin/user_edit_with_password_reset.html'
    child_links = (('Channels', 'channel', None),)

    form_excluded_columns = ('date_updated', 'channels', 'flags', 'activity', 'external_friends', 'user_promotion', 'video_instance_rel')

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

    def after_model_change(self, form, model, is_created):
        if not model.is_active:
            channels = video_models.Channel.query.filter(
                video_models.Channel.owner == model.id,
                video_models.Channel.public == True)
            for channel in channels:
                channel.visible = False
                channel.public = False
                channel.save()

    @expose('/twitter_screenname/', methods=['POST'])
    def twitter_screenname(self):
        userid = request.form['user_id']
        screen_name = request.form['screenname']
        redirect_url = url_for('user.edit_view') + '?id=' + userid

        if auth_models.ExternalToken.query.filter_by(
                user=userid, external_system='twitter').count():
            flash('User already has Twitter record', 'error')
            return redirect(redirect_url)

        api = twitter.Api(
            consumer_key=app.config['TWITTER_CONSUMER_KEY'],
            consumer_secret=app.config['TWITTER_CONSUMER_SECRET'],
            access_token_key=app.config['TWITTER_ACCESS_TOKEN_KEY'],
            access_token_secret=app.config['TWITTER_ACCESS_TOKEN_SECRET'])
        try:
            external_uid = api.GetUser(screen_name=screen_name).id
        except:
            app.logger.exception('Error fetching twitter data for "%s"', screen_name)
            flash('Unable to fetch Twitter user data', 'error')
            return redirect(redirect_url)

        auth_models.ExternalToken(
            user=userid,
            external_system='twitter',
            external_uid=external_uid,
            external_token='xxx',
            expires='2100-01-01',
            meta=json.dumps(dict(screen_name=screen_name))
        ).save()

        return redirect(redirect_url + '#external_tokens-0')


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

    @expose('/check_filter/', methods=['POST'])
    def check_filter(self):
        try:
            _filter_validator(None, type('Field', (object,), dict(data=request.form['filter']))())
        except wtf.ValidationError as e:
            return jsonify(error=e.message), 400
        users = models.BroadcastMessage(
            filter=request.form['filter'],
            external_system=request.form['external_system']
        ).get_users()
        return jsonify(user_count=users.count())
