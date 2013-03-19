from sqlalchemy import desc
from flask import abort, request, g
from flask.ext import wtf
from flask.ext.admin import form
from wtforms.validators import ValidationError
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.webservice import WebService, expose_ajax, ajax_create_response, process_image
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.core.youtube import get_video_data
from rockpack.mainsite.helpers.urls import url_for, url_to_endpoint
from rockpack.mainsite.helpers.db import gen_videoid
from rockpack.mainsite.services.video.models import (
    Channel, ChannelLocaleMeta, Video, VideoInstance, VideoLocaleMeta, Category)
from rockpack.mainsite.services.cover_art.models import UserCoverArt, RockpackCoverArt
from rockpack.mainsite.services.cover_art import api as cover_api
from rockpack.mainsite.services.video import api as video_api
from rockpack.mainsite.services.search import api as search_api
from .models import User, UserActivity, Subscription


ACTION_COLUMN_VALUE_MAP = dict(
    view=('view_count', 1),
    star=('star_count', 1),
    unstar=('star_count', -1),
)


def get_or_create_video_record(search_instance_id, locale):
    try:
        prefix, source, source_videoid = search_instance_id.split('-', 2)
        source = int(source)
    except ValueError:
        abort(400)
    assert source == 1
    video_id = gen_videoid(None, source, source_videoid)
    if not Video.query.filter_by(id=video_id).count():
        video_data = get_video_data(source_videoid)
        Video.add_videos(video_data.videos, source, locale)
    return video_id


@commit_on_success
def save_video_activity(user, action, instance_id, locale):
    try:
        column, value = ACTION_COLUMN_VALUE_MAP[action]
    except KeyError:
        abort(400, message='invalid action')

    instance = VideoInstance.query.filter_by(id=instance_id)
    if instance_id.startswith(search_api.VIDEO_INSTANCE_PREFIX):
        video_id = get_or_create_video_record(instance_id, locale)
    else:
        video_id = instance.value(VideoInstance.video)
        if not video_id:
            abort(400, message='video_instance not found')

    if action == 'view':
        object_type = 'video_instance'
        object_id = instance_id
    else:
        object_type = 'video'
        object_id = video_id

    activity = dict(user=user, action=action,
                    object_type=object_type, object_id=object_id)
    if not UserActivity.query.filter_by(**activity).count():
        # Increment value on each of instance, video, & locale meta
        video = Video.query.filter_by(id=video_id)
        meta = VideoLocaleMeta.query.filter_by(video=video_id, locale=locale)
        incr = lambda m: {getattr(m, column): getattr(m, column) + value}
        instance.update(incr(VideoInstance))
        updated = video.update(incr(Video))
        assert updated
        updated = meta.update(incr(VideoLocaleMeta))
        if not updated:
            meta = Video.query.get(video_id).add_meta(locale)
            setattr(meta, column, 1)

    UserActivity(**activity).save()

    if action in ('star', 'unstar'):
        channel = Channel.query.filter_by(
            owner=user, title=app.config['FAVOURITE_CHANNEL'][0]).first()
        if channel:
            if action == 'unstar':
                channel.remove_videos([object_id])
            else:
                channel.add_videos([object_id])


def action_object_list(user, action, limit):
    query = UserActivity.query.filter_by(user=user, action=action).\
        order_by(desc('id')).limit(limit)
    id_list = zip(*query.values('object_id'))
    return id_list[0] if id_list else []


def user_subscriptions(userid):
    return Subscription.query.filter_by(user=userid)


def check_present(form, field):
    if field.name not in (request.json or request.form):
        raise ValidationError('This field is required, but can be an empty string.')


def verify_id_on_model(model, col='id'):
    def f(form, field):
        if field.data:
            if not model.query.filter_by(**{col: field.data}).count():
                raise ValidationError('Invalid {}: {}'.format(field.name, field.data))
    return f


class ChannelForm(form.BaseForm):
    def __init__(self, *args, **kwargs):
        super(ChannelForm, self).__init__(*args, **kwargs)
        self._channel_id = None

    title = wtf.TextField(validators=[check_present])
    description = wtf.TextField(validators=[check_present])
    category = wtf.TextField(validators=[check_present, verify_id_on_model(Category)])
    cover = wtf.TextField(validators=[check_present])
    public = wtf.BooleanField(validators=[check_present])

    def for_channel_id(self, id):
        self._channel_id = id

    def validate_cover(self, field):
        exists = lambda m: m.query.filter_by(cover=field.data).count()
        if field.data and not (exists(RockpackCoverArt) or exists(UserCoverArt)):
            raise ValidationError('Invalid cover reference')

    def validate_title(self, field):
        user_channels = Channel.query.filter_by(owner=self.userid)
        if not field.data:
            untitled_channel = app.config['UNTITLED_CHANNEL'] + ' '
            count = user_channels.filter(Channel.title.like(untitled_channel + '%')).count()
            field.data = untitled_channel + str(count + 1)

        # If we have a channel with the same title, other than the one we're editing, ...
        if user_channels.filter_by(title=field.data, deleted=False).count() and not (
                self._channel_id and user_channels.filter_by(id=self._channel_id).count()):
            raise ValidationError('Duplicate title')

    def validate_category(self, field):
        if not (field.data and Category.query.get(field.data)):
            raise ValidationError('invalid category')


class ActivityForm(wtf.Form):
    action = wtf.SelectField(choices=ACTION_COLUMN_VALUE_MAP.items())
    video_instance = wtf.StringField(validators=[wtf.Required()])


def _channel_info_response(channel, locale, paging, owner_url):
    data = video_api.channel_dict(channel, owner_url=owner_url)
    items, total = video_api.get_local_videos(locale, paging, channel=channel.id, with_channel=False)
    data['videos'] = dict(items=items, total=total)
    return data


class UserWS(WebService):

    endpoint = '/'

    @expose_ajax('/<userid>/', cache_age=60, secure=False)
    def user_info(self, userid):
        user = User.query.get_or_404(userid)
        channels = [video_api.channel_dict(c, with_owner=False, owner_url=False) for c in
                    Channel.query.filter_by(owner=user.id, deleted=False, public=True)]
        return dict(
            id=user.id,
            name=user.username,     # XXX: backwards compatibility
            username=user.username,
            display_name=user.display_name,
            avatar_thumbnail_url=user.avatar.thumbnail_small,
            channels=dict(items=channels, total=len(channels)),
        )

    @expose_ajax('/<userid>/', cache_private=True)
    @check_authorization()
    def own_user_info(self, userid):
        if not userid == g.authorized.userid:
            return self.user_info(userid)
        user = g.authorized.user
        channels = [video_api.channel_dict(c, with_owner=False, owner_url=True) for c in
                    Channel.query.filter_by(owner=user.id, deleted=False)]
        info = dict(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            avatar_thumbnail_url=user.avatar.thumbnail_small,
            date_of_birth=user.date_of_birth.isoformat() if user.date_of_birth else None,
        )
        for key in 'channels', 'activity', 'cover_art', 'subscriptions':
            info[key] = dict(resource_url=url_for('userws.get_%s' % key, userid=userid))
        info['channels'].update(items=channels, total=len(channels))
        return info

    @expose_ajax('/<userid>/<any("username"):attribute_name>/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def change_user_info(self, userid, attribute_name):
        user = g.authorized.user
        if user.username_updated:
            abort(400, message='Limit for changing username has been reached')
        username = request.json
        if not isinstance(username, str) or username != User.sanitise_username(username):
            abort(400, message='Not a valid username')
        suggested = User.suggested_username(username)
        if suggested != username:
            abort(400, message='Username is already taken', suggested_username=suggested)
        user.username = username
        user.username_updated = True
        user.save()
        return 204

    @expose_ajax('/<userid>/avatar/', cache_age=60)
    def get_avatar(self, userid):
        user = User.query.get_or_404(userid)
        return None, 302, [('Location', user.avatar.thumbnail_large)]

    @expose_ajax('/<userid>/avatar/', methods=['PUT'])
    @check_authorization(self_auth=True)
    def set_avatar(self, userid):
        user = User.query.get_or_404(userid)
        user.avatar = process_image(User.avatar)
        user.save()
        return None, 204, [('Location', user.avatar.thumbnail_large)]

    @expose_ajax('/<userid>/activity/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_activity(self, userid):
        subscriptions = user_subscriptions(userid).\
            order_by(desc('date_created')).limit(self.max_page_size)
        return dict(
            recently_viewed=action_object_list(userid, 'view', self.max_page_size),
            recently_starred=action_object_list(userid, 'star', self.max_page_size),
            subscribed=[id for (id,) in subscriptions.values('channel')],
        )

    @expose_ajax('/<userid>/activity/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_activity(self, userid):
        form = ActivityForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)
        save_video_activity(userid,
                            form.action.data,
                            form.video_instance.data,
                            self.get_locale())

    @expose_ajax('/<userid>/channels/', cache_private=True)
    @check_authorization(self_auth=True)
    def get_channels(self, userid):
        channels = [video_api.channel_dict(c, with_owner=False, owner_url=True) for c in
                    Channel.query.filter_by(owner=userid, deleted=False)]
        return dict(channels=dict(items=channels, total=len(channels)))

    @expose_ajax('/<userid>/channels/', methods=('POST',))
    @check_authorization(self_auth=True)
    def channel_item_create(self, userid):
        form = ChannelForm(csrf_enabled=False)
        form.userid = userid
        if not form.validate():
            abort(400, form_errors=form.errors)
        channel = Channel.create(
            owner=form.userid,
            title=form.title.data,
            description=form.description.data,
            cover=form.cover.data,
            category=form.category.data,
            public=form.public.data)
        return ajax_create_response(channel)

    @expose_ajax('/<userid>/channels/<channelid>/', cache_age=60, secure=False)
    def channel_info(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, public=True, deleted=False).first_or_404()
        return _channel_info_response(channel, self.get_locale(), self.get_page(), False)

    @expose_ajax('/<userid>/channels/<channelid>/', cache_age=0)
    @check_authorization()
    def owner_channel_info(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if g.authorized.userid != userid and not channel.public:
            abort(404)
        return _channel_info_response(channel, self.get_locale(), self.get_page(), True)

    @expose_ajax('/<userid>/channels/<channelid>/public/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def channel_public_toggle(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        if not isinstance(request.json, bool):
            abort(400, form_errors="Value should be 'true' or 'false'")
        channel.public = request.json
        channel = channel.save()
        return '{}'.format(str(channel.public).lower())

    @expose_ajax('/<userid>/channels/<channelid>/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def channel_item_edit(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        form = ChannelForm(csrf_enabled=False)
        form.userid = userid
        if not form.validate():
            abort(400, form_errors=form.errors)

        channel.title = form.title.data
        channel.description = form.description.data
        channel.cover = form.cover.data
        channel.public = Channel.should_be_public(channel, form.public.data)
        channel.save()

        # Update metas to a new category if necessary
        for m in list(ChannelLocaleMeta.query.filter_by(channel=channelid)):
            # NOTE: If we change the category, and there isn't a mapping to
            # a locale for it, set it as per the form
            if int(form.category.data) != m.category:
                m.category = Category.map_to(int(form.category.data), m.locale)\
                    or form.category.data

                m.save()
        resource_url = channel.get_resource_url(True)
        return (dict(id=channel.id, resource_url=resource_url),
                200, [('Location', resource_url)])

    @expose_ajax('/<userid>/channels/<channelid>/videos/')
    @check_authorization()
    def channel_videos(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        return [v[0] for v in VideoInstance.query.filter_by(channel=channelid).order_by('position asc').values('video')]

    @expose_ajax('/<userid>/channels/<channelid>/videos/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def update_channel_videos(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)

        if not request.json or not isinstance(request.json, list):
            abort(400, message='List can be empty, but must be present')

        additions = []
        instances = {v.video: v for v in list(VideoInstance.query.filter_by(channel=channelid).order_by('position asc'))}
        for pos, vid in enumerate(request.json):
            if not isinstance(vid, str):
                abort(400, message='List item must be a video id')
            i = instances.get(vid)
            if not i:
                additions.append(vid)
                continue
            if i.position != pos:
                i.position = pos
                g.session.add(i)

        # Get a valid list of video ids
        video_ids = Video.query.filter(Video.id.in_(additions)).values('id')
        for v in video_ids:
            g.session.add(VideoInstance(video=v, channel=channelid))

        deletes = set(instances.keys()).difference([v for v in request.json])
        if deletes:
            VideoInstance.query.filter(
                VideoInstance.video.in_(deletes),
                VideoInstance.channel == channelid
            ).delete(synchronize_session='fetch')

        try:
            g.session.commit()
        except Exception as e:
            g.session.rollback()
            app.logger.error('Failed to update channel videos with: {}'.format(str(e)))
            abort(500)
        return 204

    @expose_ajax('/<userid>/channels/<channelid>/', methods=('DELETE',))
    @check_authorization(self_auth=True)
    def channel_delete(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        channel.deleted = True
        channel.save()
        return 204

    @expose_ajax('/<userid>/cover_art/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_cover_art(self, userid):
        covers = UserCoverArt.query.filter_by(owner=userid)
        return cover_api.cover_art_response(covers, self.get_page(), own=True)

    @expose_ajax('/<userid>/cover_art/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_cover_art(self, userid):
        path = process_image(UserCoverArt.cover)
        cover = UserCoverArt(cover=path, owner=userid).save()
        return ajax_create_response(cover, cover_api.cover_art_dict(cover, own=True))

    @expose_ajax('/<userid>/cover_art/<ref>', cache_age=3600)
    def redirect_cover_art_item(self, userid, ref):
        cover = UserCoverArt.query.filter_by(cover=ref).first_or_404()
        return None, 302, [('Location', cover.cover.background)]

    @expose_ajax('/<userid>/cover_art/<ref>', methods=['DELETE'])
    @check_authorization(self_auth=True)
    @commit_on_success
    def delete_cover_art_item(self, userid, ref):
        if not UserCoverArt.query.filter_by(cover=ref).delete():
            abort(404)

    @expose_ajax('/<userid>/subscriptions/')
    @check_authorization(self_auth=True)
    def get_subscriptions(self, userid):
        channels = user_subscriptions(userid).join(Channel).filter(Channel.deleted==False).values('id', 'owner')
        items = [dict(resource_url=url_for('userws.delete_subscription_item',
                                           userid=userid, channelid=channelid),
                      channel_url=url_for('userws.channel_info',
                                          userid=owner, channelid=channelid))
                 for channelid, owner in channels]
        return dict(subscriptions=dict(items=items, total=len(items)))

    @expose_ajax('/<userid>/subscriptions/', methods=['POST'])
    @check_authorization(self_auth=True)
    def create_subscription(self, userid):
        endpoint, args = url_to_endpoint(request.json or '')
        if endpoint not in ('userws.owner_channel_info', 'userws.channel_info'):
            abort(400, message='Invalid channel url')
        channelid = args['channelid']
        if not Channel.query.filter_by(id=channelid, deleted=False).count():
            abort(400, message='Channel not found')
        subs = Subscription(user=userid, channel=channelid).save()
        return ajax_create_response(subs)

    @expose_ajax('/<userid>/subscriptions/<channelid>/')
    @check_authorization(self_auth=True)
    def redirect_subscription_item(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        return channel.resource_url, 302, [('Location', channel.resource_url)]

    @expose_ajax('/<userid>/subscriptions/<channelid>/', methods=['DELETE'])
    @check_authorization(self_auth=True)
    @commit_on_success
    def delete_subscription_item(self, userid, channelid):
        if not user_subscriptions(userid).filter_by(channel=channelid).delete():
            abort(404)

    # TODO: remove me - needed for backwards compatibility with iOS app prototype
    @expose_ajax('/USERID/subscriptions/recent_videos/', cache_age=60)
    def all_recent_videos(self):
        data, total = video_api.get_local_videos(self.get_locale(), self.get_page(), date_order=True, **request.args)
        return {'videos': {'items': data, 'total': total}}

    @expose_ajax('/<userid>/subscriptions/recent_videos/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def recent_videos(self, userid):
        channels = user_subscriptions(userid)
        if channels.count():
            data, total = video_api.get_local_videos(self.get_locale(), self.get_page(),
                                                     date_order=True, channels=channels.values('channel'))
        else:
            data, total = [], 0
        return {'videos': {'items': data, 'total': total}}
