from werkzeug.datastructures import MultiDict
from sqlalchemy import desc
from sqlalchemy.orm import lazyload
from sqlalchemy.orm.exc import NoResultFound
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
    Channel, ChannelLocaleMeta, Video, VideoInstance, VideoInstanceLocaleMeta, Category, ContentReport)
from rockpack.mainsite.services.oauth.api import RockRegistrationForm
from rockpack.mainsite.services.cover_art.models import UserCoverArt, RockpackCoverArt
from rockpack.mainsite.services.cover_art import api as cover_api
from rockpack.mainsite.services.video import api as video_api
from rockpack.mainsite.services.search import api as search_api
from .models import User, UserActivity, Subscription


ACTION_COLUMN_VALUE_MAP = dict(
    view=('view_count', 1),
    select=('view_count', 1),
    star=('star_count', 1),
    unstar=('star_count', -1),
    subscribe=('subscriber_count', 1),
    unsubscribe=('subscriber_count', -1),
)


ACTIVITY_OBJECT_TYPE_MAP = dict(
    user=User,
    channel=Channel,
    video=Video,
    video_instance=VideoInstance,
)


@commit_on_success
def get_or_create_video_records(instance_ids, locale):
    """Take a list of instance ids and return mapping to associated video ids."""

    # Split between "fake" search ids and real
    search_instance_ids = set()
    real_instance_ids = set()
    for instance_id in instance_ids:
        if instance_id.startswith(search_api.VIDEO_INSTANCE_PREFIX):
            search_instance_ids.add(instance_id)
        else:
            real_instance_ids.add(instance_id)

    # Check if any "real" ids are invalid
    if real_instance_ids:
        instances = VideoInstance.query.filter(VideoInstance.id.in_(real_instance_ids))
        existing_ids = dict(instances.values('id', 'video'))
        invalid = list(real_instance_ids - set(existing_ids.keys()))
        if invalid:
            abort(400, message='Invalid video instance ids', data=invalid)
    else:
        existing_ids = {}

    if not search_instance_ids:
        return existing_ids

    # Map search ids to real ids
    video_id_map = dict()
    invalid = []
    for instance_id in search_instance_ids:
        try:
            prefix, source, source_videoid = instance_id.split('-', 2)
            source = int(source)
        except ValueError:
            invalid.append(instance_id)
        else:
            video_id = gen_videoid(None, source, source_videoid)
            video_id_map[video_id] = instance_id, source, source_videoid
            existing_ids[instance_id] = video_id
    if invalid:
        abort(400, message='Invalid video instance ids', data=invalid)

    # Check which video references from search instances already exist
    # and create records for any that don't
    search_video_ids = set(video_id_map.keys())
    existing_video_ids = set(
        v[0] for v in Video.query.filter(Video.id.in_(search_video_ids)).values('id'))
    new_ids = search_video_ids - existing_video_ids
    for video_id in new_ids:
        instance_id, source, source_videoid = video_id_map[video_id]
        # TODO: Use youtube batch request feature
        try:
            video_data = get_video_data(source_videoid)
        except Exception:
            abort(400, message='Invalid video instance ids', data=[instance_id])
        Video.add_videos(video_data.videos, source, locale)

    return existing_ids


@commit_on_success
def save_video_activity(user, action, instance_id, locale):
    try:
        column, value = ACTION_COLUMN_VALUE_MAP[action]
    except KeyError:
        abort(400, message='invalid action')

    video_id = get_or_create_video_records([instance_id], locale)[instance_id]
    activity = dict(user=user, action=action,
                    object_type='video', object_id=video_id)
    if not UserActivity.query.filter_by(**activity).count():
        # Increment value on each of instance, video, & locale meta
        incr = lambda m: {getattr(m, column): getattr(m, column) + value}
        updated = Video.query.filter_by(id=video_id).update(incr(Video))
        assert updated
        if not instance_id.startswith(search_api.VIDEO_INSTANCE_PREFIX):
            VideoInstance.query.filter_by(id=instance_id).update(incr(VideoInstance))
            meta = VideoInstanceLocaleMeta.query.filter_by(video_instance=instance_id, locale=locale)
            updated = meta.update(incr(VideoInstanceLocaleMeta))
            if not updated:
                meta = VideoInstance.query.get(instance_id).add_meta(locale)
                setattr(meta, column, 1)

    UserActivity(**activity).save()

    if action in ('star', 'unstar'):
        channel = Channel.query.filter_by(
            owner=user, title=app.config['FAVOURITE_CHANNEL'][0]).first()
        if channel:
            if action == 'unstar':
                channel.remove_videos([video_id])
            else:
                channel.add_videos([video_id])


@commit_on_success
def save_channel_activity(channelid, action, locale):
    """Update channel with subscriber, view, or star count changes."""
    try:
        column, value = ACTION_COLUMN_VALUE_MAP[action]
    except KeyError:
        abort(400, message='invalid action')
    incr = lambda m: {getattr(m, column): getattr(m, column) + value}
    # Update channel record:
    Channel.query.filter_by(id=channelid).update(incr(Channel))
    # Update or create locale meta record:
    ChannelLocaleMeta.query.filter_by(channel=channelid, locale=locale).update(incr(ChannelLocaleMeta)) or \
        ChannelLocaleMeta(channel=channelid, locale=locale, **{column: value}).save()


@commit_on_success
def save_content_report(user, object_type, object_id):
    activity = dict(action='content_reported', user=user,
                    object_type=object_type, object_id=object_id)
    if not UserActivity.query.filter_by(**activity).count():
        UserActivity(**activity).save()
    report = dict(object_type=object_type, object_id=object_id)
    updated = ContentReport.query.filter_by(**report).update(
        {ContentReport.count: ContentReport.count + 1})
    if not updated:
        report = ContentReport(**report).save()


@commit_on_success
def add_videos_to_channel(channel, instance_list, locale):
    if all(i.startswith('RP') for i in instance_list):
        # Backwards compatibility
        id_map = dict((v[0], v[0]) for v in Video.query.filter(Video.id.in_(instance_list)).values('id'))
    else:
        id_map = get_or_create_video_records(instance_list, locale)
    existing = dict((v.video, v) for v in VideoInstance.query.filter_by(channel=channel.id))
    added = []
    for position, instance_id in enumerate(instance_list):
        video_id = id_map[instance_id]
        if video_id not in added:
            instance = existing.get(video_id) or VideoInstance(video=video_id, channel=channel.id)
            instance.position = position
            VideoInstance.query.session.add(instance)
            added.append(video_id)

    deleted_video_ids = set(existing.keys()).difference(id_map.values())
    if deleted_video_ids:
        VideoInstance.query.filter(
            VideoInstance.video.in_(deleted_video_ids),
            VideoInstance.channel == channel.id
        ).delete(synchronize_session='fetch')


def _user_list(paging, **filters):
    users = User.query

    if filters.get('subscribed_to'):
        users = users.join(Subscription, Subscription.user == User.id).\
            filter_by(channel=filters['subscribed_to'])

    total = users.count()
    offset, limit = paging
    users = users.offset(offset).limit(limit)
    items = []
    for position, user in enumerate(users, offset):
        items.append(dict(
            position=position,
            id=user.id,
            resource_url=user.get_resource_url(),
            display_name=user.display_name,
            avatar_thumbnail_url=user.avatar.thumbnail_small,
        ))
    return items, total


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


class ChannelForm(form.BaseForm):
    def __init__(self, *args, **kwargs):
        super(ChannelForm, self).__init__(*args, **kwargs)
        self._channel_id = None

    title = wtf.TextField(validators=[check_present])
    description = wtf.TextField(validators=[check_present])
    category = wtf.TextField(validators=[check_present])
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
        if field.data:
            try:
                field.data = Category.query.get(int(field.data)).id
            except (ValueError, AttributeError):
                raise ValidationError('invalid category')
        else:
            field.data = None


class ActivityForm(wtf.Form):
    action = wtf.SelectField(choices=ACTION_COLUMN_VALUE_MAP.items())
    video_instance = wtf.StringField(validators=[wtf.Required()])


class ContentReportForm(wtf.Form):
    object_type = wtf.SelectField(choices=ACTIVITY_OBJECT_TYPE_MAP.items())
    object_id = wtf.StringField(validators=[wtf.Required()])

    def validate_object_id(self, field):
        object_type = ACTIVITY_OBJECT_TYPE_MAP.get(self.object_type.data)
        if object_type and not object_type.query.filter_by(id=field.data).count():
            raise ValidationError('invalid id')


def _channel_info_response(channel, locale, paging, owner_url):
    data = video_api.channel_dict(channel, owner_url=owner_url)
    items, total = video_api.get_local_videos(
        locale, paging, channel=channel.id, with_channel=False,
        position_order=True, date_order=True)
    data['ecommerce_url'] = channel.ecommerce_url
    data['category'] = channel.category
    data['videos'] = dict(items=items, total=total)
    return data


class UserWS(WebService):

    endpoint = '/'

    @expose_ajax('/<userid>/', cache_age=60, secure=False)
    def user_info(self, userid):
        user = User.query.get_or_404(userid)
        channels = [video_api.channel_dict(c, with_owner=False, owner_url=False)
                    for c in Channel.query.options(lazyload('category_rel')).
                    filter_by(owner=user.id, deleted=False, public=True)]
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
            gender=user.gender,
            avatar_thumbnail_url=user.avatar.thumbnail_small,
            date_of_birth=user.date_of_birth.isoformat() if user.date_of_birth else None,
        )
        for key in 'channels', 'activity', 'cover_art', 'subscriptions':
            info[key] = dict(resource_url=url_for('userws.post_%s' % key, userid=userid))
        info['channels'].update(items=channels, total=len(channels))
        return info

    @expose_ajax('/<userid>/<any("username", "first_name", "last_name", "email", "password", "locale", "date_of_birth", "gender"):attribute_name>/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def change_user_info(self, userid, attribute_name):
        value = request.json
        form = RockRegistrationForm(formdata=MultiDict([(attribute_name, value)]), csrf_enabled=False)
        field = getattr(form, attribute_name)
        if not field.validate(field.data):
            response = {'message': field.errors}
            # special case for username
            if attribute_name == 'username':
                response.update({'suggested_username': User.suggested_username(value)})
            abort(400, **response)
        user = g.authorized.user
        # special case for password
        if attribute_name == 'password':
            user.set_password(form.password.data)
        else:
            setattr(user, attribute_name, field.data)
        if attribute_name == 'username':
            if user.username_updated:
                abort(400, message='Limit for changing username has been reached')
            user.username_updated = True
        user.save()

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
        ids = dict((key, action_object_list(userid, key, self.max_page_size))
                   for key in ACTION_COLUMN_VALUE_MAP)
        return dict(
            recently_viewed=ids['view'],
            recently_starred=list(set(ids['star']) - set(ids['unstar'])),
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
        channelid = VideoInstance.query.filter_by(id=form.video_instance.data).value('channel')
        if channelid:
            save_channel_activity(channelid, form.action.data, self.get_locale())

    @expose_ajax('/<userid>/content_reports/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_content_report(self, userid):
        form = ContentReportForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)
        save_content_report(userid, form.object_type.data, form.object_id.data)

    @expose_ajax('/<userid>/channels/', cache_private=True)
    @check_authorization(self_auth=True)
    def get_channels(self, userid):
        channels = [video_api.channel_dict(c, with_owner=False, owner_url=True) for c in
                    Channel.query.filter_by(owner=userid, deleted=False)]
        return dict(channels=dict(items=channels, total=len(channels)))

    @expose_ajax('/<userid>/channels/', methods=('POST',))
    @check_authorization(self_auth=True)
    def post_channels(self, userid):
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
        if not app.config.get('ELASTICSEARCH_URL'):
            channel = Channel.query.filter_by(id=channelid, public=True, deleted=False).first_or_404()
            return _channel_info_response(channel, self.get_locale(), self.get_page(), False)

        channel, total = video_api.es_get_channels_with_videos(channel_ids=[channelid])
        if not channel:
            abort(404)
        return channel[0]

    @expose_ajax('/<userid>/channels/<channelid>/', cache_age=0)
    @check_authorization()
    def owner_channel_info(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if g.authorized.userid != userid and not channel.public:
            abort(404)
        return _channel_info_response(channel, self.get_locale(), self.get_page(), True)

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
        channel.category = form.category.data
        channel.public = Channel.should_be_public(channel, form.public.data)
        channel.save()

        resource_url = channel.get_resource_url(True)
        return (dict(id=channel.id, resource_url=resource_url),
                200, [('Location', resource_url)])

    @expose_ajax('/<userid>/channels/<channelid>/', methods=('DELETE',))
    @check_authorization(self_auth=True)
    def channel_delete(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        channel.deleted = True
        channel.save()

    @expose_ajax('/<userid>/channels/<channelid>/public/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def channel_public_toggle(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        if not isinstance(request.json, bool):
            abort(400, message="Boolean value required")
        channel.public = request.json
        channel = channel.save()
        return channel.public

    @expose_ajax('/<userid>/channels/<channelid>/videos/')
    @check_authorization()
    def channel_videos(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        return [v[0] for v in VideoInstance.query.filter_by(channel=channelid).order_by('position').values('video')]

    @expose_ajax('/<userid>/channels/<channelid>/videos/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def update_channel_videos(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        if not request.json or not isinstance(request.json, list):
            abort(400, message='List can be empty, but must be present')
        add_videos_to_channel(channel, map(str, request.json), self.get_locale())

    @expose_ajax('/<userid>/channels/<channelid>/subscribers/', cache_age=60)
    def channel_subscribers(self, userid, channelid):
        items, total = _user_list(self.get_page(), subscribed_to=channelid)
        return dict(users=dict(items=items, total=total))

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
    def get_subscriptions(self, userid):
        subscriptions = user_subscriptions(userid)
        if subscriptions.count():
            channels = [s[0] for s in subscriptions.values('channel')]
            items, total = video_api.get_local_channel(
                self.get_locale(), self.get_page(), channels=channels)
        else:
            items, total = [], 0
        for item in items:
            item['subscription_resource_url'] =\
                url_for('userws.delete_subscription_item', userid=userid, channelid=item['id'])
        return dict(channels=dict(items=items, total=total))

    @expose_ajax('/<userid>/subscriptions/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_subscriptions(self, userid):
        endpoint, args = url_to_endpoint(request.json or '')
        if endpoint not in ('userws.owner_channel_info', 'userws.channel_info'):
            abort(400, message='Invalid channel url')
        channelid = args['channelid']
        if not Channel.query.filter_by(id=channelid, deleted=False).count():
            abort(400, message='Channel not found')
        if Subscription.query.filter_by(user=userid, channel=channelid).count():
            abort(400, message='Already subscribed')
        subs = Subscription(user=userid, channel=channelid).save()
        save_channel_activity(channelid, 'subscribe', self.get_locale())
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
        save_channel_activity(channelid, 'unsubscribe', self.get_locale())

    @expose_ajax('/<userid>/subscriptions/recent_videos/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def recent_videos(self, userid):
        subscriptions = user_subscriptions(userid)
        if subscriptions.count():
            channels = [s[0] for s in subscriptions.values('channel')]
            items, total = video_api.get_local_videos(self.get_locale(), self.get_page(),
                                                      date_order=True, channels=channels)
        else:
            items, total = [], 0
        return dict(videos=dict(items=items, total=total))
