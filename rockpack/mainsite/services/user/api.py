from werkzeug.datastructures import MultiDict
from sqlalchemy import desc, func
from sqlalchemy.orm import lazyload, contains_eager
from flask import abort, request, json, g
from flask.ext import wtf
from flask.ext.admin import form
from wtforms.validators import ValidationError
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.webservice import WebService, expose_ajax, ajax_create_response, process_image
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.core.youtube import get_video_data
from rockpack.mainsite.core.es import use_elasticsearch, api
from rockpack.mainsite.helpers import lazy_gettext as _
from rockpack.mainsite.helpers.forms import naughty_word_validator
from rockpack.mainsite.helpers.urls import url_for, url_to_endpoint
from rockpack.mainsite.helpers.db import gen_videoid, get_column_validators, get_box_value
from rockpack.mainsite.services.video.models import (
    Channel, ChannelLocaleMeta, Video, VideoInstance, VideoInstanceLocaleMeta, Category, ContentReport)
from rockpack.mainsite.services.oauth.api import (
    RockRegistrationForm, external_user_from_token_form, record_user_event)
from rockpack.mainsite.services.oauth.models import ExternalFriend, ExternalToken
from rockpack.mainsite.services.cover_art.models import UserCoverArt, RockpackCoverArt
from rockpack.mainsite.services.cover_art import api as cover_api
from rockpack.mainsite.services.video import api as video_api
from rockpack.mainsite.services.search import api as search_api
from .models import User, UserActivity, UserNotification, Subscription


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
def get_or_create_video_records(instance_ids):
    """Take a list of instance ids and return mapping to associated video ids."""
    def add(s, i):
        if i and i not in s:
            s.add(i)
            instance_id_order.append(i)

    # Split between "fake" external ids and real
    external_instance_ids = set()
    real_instance_ids = set()
    invalid = []
    instance_id_order = []
    for instance_id in instance_ids:
        try:
            if instance_id.startswith(search_api.VIDEO_INSTANCE_PREFIX):
                prefix, source, source_videoid = instance_id.split('-', 2)
                add(external_instance_ids, (int(source), source_videoid))
            else:
                add(real_instance_ids, instance_id)
        except (AttributeError, ValueError):  # not a string
            try:
                source, source_videoid = instance_id
                source = ['rockpack', 'youtube'].index(source)  # TODO: use db mapping
                assert len(source_videoid)
                add(external_instance_ids, (source, source_videoid))
            except (TypeError, ValueError, AssertionError):
                invalid.append(instance_id)
    if invalid:
        abort(400, message=_('Invalid video instance ids'), data=invalid)

    # Check if any "real" ids are invalid
    if real_instance_ids:
        instances = VideoInstance.query.filter(VideoInstance.id.in_(real_instance_ids))
        existing_ids = dict(instances.values('id', 'video'))
        invalid = list(real_instance_ids - set(existing_ids.keys()))
        if invalid:
            abort(400, message=_('Invalid video instance ids'), data=invalid)
    else:
        existing_ids = {}

    if external_instance_ids:
        # Map search ids to real ids
        video_id_map = dict()
        for source, source_videoid in external_instance_ids:
            video_id = gen_videoid(None, source, source_videoid)
            video_id_map[video_id] = source, source_videoid
            existing_ids[(source, source_videoid)] = video_id

        # Check which video references from search instances already exist
        # and create records for any that don't
        search_video_ids = set(video_id_map.keys())
        existing_video_ids = set(
            v[0] for v in Video.query.filter(Video.id.in_(search_video_ids)).values('id'))
        new_ids = search_video_ids - existing_video_ids
        for video_id in new_ids:
            source, source_videoid = video_id_map[video_id]
            # TODO: Use youtube batch request feature
            try:
                assert source == 1
                video_data = get_video_data(source_videoid)
            except Exception:
                abort(400, message=_('Invalid video instance ids'), data=[[source, source_videoid]])
            Video.add_videos(video_data.videos, source)

    return [existing_ids[id] for id in instance_id_order]


@commit_on_success
def save_video_activity(userid, action, instance_id, locale):
    try:
        column, value = ACTION_COLUMN_VALUE_MAP[action]
    except KeyError:
        abort(400, message=_('Invalid action'))

    video_id = get_or_create_video_records([instance_id])[0]
    activity = dict(user=userid, action=action,
                    object_type='video_instance', object_id=instance_id)
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
        channel = Channel.query.filter_by(owner=userid, favourite=True).first()
        if channel:
            if action == 'unstar':
                channel.remove_videos([video_id])
            else:
                # Return new instance here so that it can be shared
                return channel.add_videos([video_id])[0]


@commit_on_success
def save_channel_activity(userid, action, channelid, locale):
    """Update channel with subscriber, view, or star count changes."""
    try:
        column, value = ACTION_COLUMN_VALUE_MAP[action]
    except KeyError:
        abort(400, message=_('Invalid action'))
    incr = lambda m: {getattr(m, column): getattr(m, column) + value}
    # Update channel record:
    Channel.query.filter_by(id=channelid).update(incr(Channel))
    # Update or create locale meta record:
    ChannelLocaleMeta.query.filter_by(channel=channelid, locale=locale).update(incr(ChannelLocaleMeta)) or \
        ChannelLocaleMeta(channel=channelid, locale=locale, **{column: value}).save()
    if action in ('subscribe', 'unsubscribe'):
        UserActivity(user=userid, action=action, object_type='channel', object_id=channelid).save()


@commit_on_success
def save_content_report(userid, object_type, object_id, reason):
    activity = dict(action='content_reported', user=userid,
                    object_type=object_type, object_id=object_id)
    if not UserActivity.query.filter_by(**activity).count():
        UserActivity(**activity).save()
    report = dict(object_type=object_type, object_id=object_id, reason=reason)
    updated = ContentReport.query.filter_by(**report).update(
        {ContentReport.count: ContentReport.count + 1})
    if not updated:
        report = ContentReport(**report).save()


@commit_on_success
def add_videos_to_channel(channel, instance_list, locale, delete_existing=False):
    video_ids = get_or_create_video_records(instance_list)
    existing = dict((v.video, v) for v in VideoInstance.query.filter_by(channel=channel.id))
    added = []
    for position, video_id in enumerate(video_ids):
        if video_id not in added:
            instance = existing.get(video_id) or VideoInstance(video=video_id, channel=channel.id)
            instance.position = position
            VideoInstance.query.session.add(instance)
            added.append(video_id)

    if delete_existing:
        deleted_video_ids = set(existing.keys()).difference(video_ids)
        if deleted_video_ids:
            VideoInstance.query.filter(
                VideoInstance.video.in_(deleted_video_ids),
                VideoInstance.channel == channel.id
            ).delete(synchronize_session='fetch')


def _user_list(paging, **filters):
    users = User.query.filter_by(is_active=True)

    if filters.get('subscribed_to'):
        users = users.join(Subscription, Subscription.user == User.id).\
            filter_by(channel=filters['subscribed_to'])

    total = users.count()
    offset, limit = paging
    users = users.order_by('date_created desc')
    users = users.offset(offset).limit(limit)
    items = []
    for position, user in enumerate(users, offset):
        items.append(dict(
            position=position,
            id=user.id,
            resource_url=user.get_resource_url(),
            display_name=user.display_name,
            avatar_thumbnail_url=user.avatar.url,
        ))
    return items, total


def _notification_list(userid, paging):
    # Old app versions don't handle new notifications :-(
    if request.rockpack_ios_version and request.rockpack_ios_version < (1, 3):
        typefilter = ('subscribed', 'starred')
    else:
        typefilter = ()
    notifications = UserNotification.query.filter_by(
        user=userid).order_by(desc('date_created'))
    total = notifications.count()
    offset, limit = paging
    notifications = notifications.offset(offset).limit(limit)
    items = [
        dict(
            id=notification.id,
            date_created=notification.date_created.isoformat(),
            message_type=notification.message_type,
            # Might be worth optimising this by substituting the
            # pre-formatted json directly into the response
            message=json.loads(notification.message),
            read=bool(notification.date_read),
        ) for notification in notifications
        if not typefilter or notification.message_type in typefilter]
    return items, total


def _notification_unread_count(userid):
    return UserNotification.query.filter_by(user=userid, date_read=None).count()


@commit_on_success
def _mark_read_notifications(userid, id_list):
    UserNotification.query.filter_by(user=userid, date_read=None).\
        filter(UserNotification.id.in_(id_list)).update(
            {UserNotification.date_read: func.now()}, False)


def action_object_list(user, action, limit):
    query = UserActivity.query.filter_by(user=user, action=action).\
        order_by(desc('id')).limit(limit)
    id_list = zip(*query.values('object_id'))
    return id_list[0] if id_list else []


def _user_subscriptions_query(userid):
    return Subscription.query.filter_by(user=userid)


def user_subscriptions(userid, locale, paging):
    subscriptions = _user_subscriptions_query(userid)
    if not subscriptions.count():
        return dict(items=[], total=0)
    subs = {s[0]: s[1] for s in subscriptions.values('channel', 'date_created')}
    items, total = video_api.get_local_channel(locale, paging, channels=subs.keys())
    items = [item for date, item in
             sorted([(subs[i['id']], i) for i in items], reverse=True)]
    for item in items:
        item['subscription_resource_url'] =\
            url_for('userws.delete_subscription_item', userid=userid, channelid=item['id'])
    return dict(items=items, total=total)


def user_channels(userid, locale, paging):
    channels = Channel.query.options(lazyload('owner_rel'), lazyload('category_rel')).\
        filter_by(owner=userid, deleted=False)
    total = channels.count()
    offset, limit = paging
    channels = channels.order_by('favourite desc', 'date_added desc').\
        offset(offset).limit(limit)
    items = [video_api.channel_dict(c, with_owner=False, owner_url=True) for c in channels]
    return dict(items=items, total=total)


def user_external_accounts(userid, locale, paging):
    items = []
    for token in ExternalToken.query.filter_by(user=userid):
        items.append(dict(resource_url=token.resource_url,
                          external_system=token.external_system,
                          external_uid=token.external_uid))
    return dict(items=items, total=len(items))


def user_activity(userid, locale, paging):
    ids = dict((key, action_object_list(userid, key, UserWS.max_page_size))
               for key in ACTION_COLUMN_VALUE_MAP)
    return dict(
        recently_viewed=ids['view'],
        recently_starred=list(set(ids['star']) - set(ids['unstar'])),
        subscribed=list(set(ids['subscribe']) - set(ids['unsubscribe'])),
    )


def check_present(form, field):
    if field.name not in (request.json or request.form):
        raise ValidationError(_('This field is required, but can be an empty string.'))


# Patch BooleanField process_formdata so that passed in values
# are checked, not just a check for the presence of the field.
class JsonBooleanField(wtf.BooleanField):
    process_formdata = wtf.Field.process_formdata


class ChannelForm(form.BaseForm):
    title = wtf.TextField(
        validators=[check_present, naughty_word_validator] +
        get_column_validators(Channel, 'title', False))
    description = wtf.TextField(
        validators=[check_present] +
        get_column_validators(Channel, 'description', False))
    category = wtf.TextField(validators=[check_present])
    cover = wtf.TextField(validators=[check_present])
    cover_aoi = wtf.Field()  # set from cover reference
    public = JsonBooleanField(validators=[check_present])

    def __init__(self, *args, **kwargs):
        self._channelid = kwargs.pop('channelid', None)
        super(ChannelForm, self).__init__(*args, **kwargs)

    def pre_validate(self):
        if self.description.data:
            self.description.data = ' '.join(map(lambda x: x.strip(), self.description.data.splitlines()))

    def validate_cover(self, field):
        if field.data:
            if self._channelid and field.data == 'KEEP':
                return
            found = False
            for model in RockpackCoverArt, UserCoverArt:
                cover = model.query.with_entities(model.cover_aoi).filter_by(cover=field.data).first()
                if cover:
                    self.cover_aoi.data = cover.cover_aoi
                    found = True
                    break
            if not found:
                raise ValidationError(_('Invalid cover reference.'))

    def validate_title(self, field):
        user_channels = Channel.query.filter_by(owner=self.userid)
        if not field.data:
            untitled_channel = app.config['UNTITLED_CHANNEL'] + ' '
            titles = [t[0].lower() for t in user_channels.filter(Channel.title.ilike(untitled_channel + '%')).values('title')]
            for i in xrange(1, 1000):
                t = untitled_channel + str(i)
                if t.lower() not in titles:
                    field.data = t
                    break

        # If this is a new channel (no channel.id) and there is an exisiting channel with dupe title, or
        # if this is an existing channel (has channel.id) and we have another existing channel with a dupe title
        # that isn't this channel, error.
        if user_channels.filter_by(title=field.data, deleted=False).filter(Channel.id != self._channelid).count():
            raise ValidationError(_('Duplicate title.'))

    def validate_category(self, field):
        if field.data:
            try:
                field.data = Category.query.get(int(field.data)).id
            except (ValueError, AttributeError):
                raise ValidationError(_('Invalid category.'))
        else:
            field.data = None


class ActivityForm(wtf.Form):
    action = wtf.SelectField(choices=ACTION_COLUMN_VALUE_MAP.items())
    video_instance = wtf.StringField(validators=[wtf.Required()])


class ContentReportForm(wtf.Form):
    object_type = wtf.SelectField(choices=ACTIVITY_OBJECT_TYPE_MAP.items())
    object_id = wtf.StringField(validators=[wtf.Required()])
    reason = wtf.StringField(validators=get_column_validators(ContentReport, 'reason'))

    def validate_object_id(self, field):
        object_type = ACTIVITY_OBJECT_TYPE_MAP.get(self.object_type.data)
        if object_type and not object_type.query.filter_by(id=field.data).count():
            raise ValidationError(_('Invalid id.'))


def _channel_videos(channelid, locale, paging, own=False):
    # Nasty hack to ensure that old iOS app version get all videos for a users
    # own channel and doesn't try to request more.
    # This is to ensure that when changes are PUT back the request should include
    # all videos, not just the first page (and hance delete the missing pages).
    paging_ = None
    if (own and paging == (0, 48) and
            request.rockpack_ios_version and request.rockpack_ios_version < (1, 3)):
        paging_ = paging
        paging = (0, 1000)
    items, total = video_api.get_local_videos(
        locale, paging, channel=channelid, with_channel=False,
        include_invisible=own, position_order=True, date_order=True)
    if paging_:
        total = min(paging_[1], total)
    return items, total


def _channel_info_response(channel, locale, paging, owner_url):
    data = video_api.channel_dict(channel, owner_url=owner_url)
    items, total = _channel_videos(channel.id, locale, paging, own=owner_url)
    data['ecommerce_url'] = channel.ecommerce_url
    data['category'] = channel.category
    data['videos'] = dict(items=items, total=total)
    return data


class UserWS(WebService):

    endpoint = '/'

    @expose_ajax('/<userid>/', cache_age=600, secure=False)
    def user_info(self, userid):
        if use_elasticsearch():
            ows = api.OwnerSearch()
            ows.add_id(userid)
            owners = ows.owners()
            if not owners:
                abort(404)
            owner = owners[0]
            ch = api.ChannelSearch(self.get_locale())
            offset, limit = self.get_page()
            ch.set_paging(offset, limit)
            ch.favourite_sort('desc')
            ch.add_sort('date_updated')
            ch.add_term('owner', userid)
            owner.setdefault('channels', {})['items'] = ch.channels(with_owners=False)
            owner['channels']['total'] = ch.total
            return owner

        user = User.query.get_or_404(userid)
        channels = [video_api.channel_dict(c, with_owner=False, owner_url=False)
                    for c in Channel.query.options(lazyload('category_rel')).
                    filter_by(owner=user.id, deleted=False, public=True).
                    order_by('favourite desc', 'channel.date_updated desc')]

        return dict(
            id=user.id,
            name=user.username,     # XXX: backwards compatibility
            username=user.username,
            display_name=user.display_name,
            avatar_thumbnail_url=user.avatar.url,
            channels=dict(items=channels, total=len(channels)),
        )

    @expose_ajax('/<userid>/', cache_private=True)
    @check_authorization()
    def own_user_info(self, userid):
        if not userid == g.authorized.userid:
            return self.user_info(userid)
        user = g.authorized.user
        info = dict(
            id=user.id,
            locale=user.locale,
            username=user.username,
            display_name=user.display_name,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            gender=user.gender,
            display_fullname=user.display_fullname,
            avatar_thumbnail_url=user.avatar.url,
            date_of_birth=user.date_of_birth.isoformat() if user.date_of_birth else None,
        )
        data_sections = request.args.getlist('data') or ['channels']
        for key in ('channels', 'activity', 'notifications', 'cover_art', 'subscriptions',
                    'friends', 'external_accounts'):
            info[key] = dict(resource_url=url_for('userws.post_%s' % key, userid=userid))
            if key in data_sections:
                get_user_data = globals().get('user_%s' % key)
                if get_user_data:
                    info[key].update(get_user_data(user.id, self.get_locale(), self.get_page()))
        info['subscriptions']['updates'] = url_for('userws.recent_videos', userid=userid)
        info['notifications'].update(unread_count=_notification_unread_count(userid))
        return info

    @expose_ajax('/<userid>/display_fullname/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def toggle_display_fullname(self, userid):
        data = request.json
        if not isinstance(data, bool):
            abort(400, message=_('Value must be a boolean.'))

        user = g.authorized.user

        if user.display_fullname != data:
            user.display_fullname = data
            user.save()
        return None, 204

    @expose_ajax('/<userid>/password/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def change_user_password(self, userid):
        data = request.json
        if not isinstance(data, dict) or not data.get('old') or not data.get('new'):
            abort(400, message=[_('Both old and new passwords must be supplied.')])

        new_p = data.get('new')
        old_p = data.get('old')

        user = g.authorized.user
        if not user.check_password(old_p):
            abort(400, message=[_('Old password is incorrect.')])

        form = RockRegistrationForm(formdata=MultiDict([('password', new_p)]), csrf_enabled=False)
        if not form.password.validate(form.password.data):
            abort(400, message=form.password.errors)

        user.change_password(user, new_p)
        return user.get_credentials()

    @expose_ajax('/<userid>/<any("username", "first_name", "last_name", "email", "locale", "date_of_birth", "gender"):attribute_name>/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def change_user_info(self, userid, attribute_name):
        value = request.json
        form = RockRegistrationForm(formdata=MultiDict([(attribute_name, value)]), csrf_enabled=False)
        field = getattr(form, attribute_name)
        if field.data is None:
            abort(400, message='No data given.')
        if not field.validate(field.data):
            response = {'message': field.errors}
            # special case for username
            if attribute_name == 'username':
                response.update({'suggested_username': User.suggested_username(value)})
            abort(400, **response)
        user = g.authorized.user
        setattr(user, attribute_name, field.data)
        if attribute_name == 'username':
            if user.username_updated:
                abort(400, message=_('Limit for changing username has been reached'))
            user.username_updated = True
        user.save()

    @expose_ajax('/<userid>/avatar/', cache_age=60)
    def get_avatar(self, userid):
        user = User.query.get_or_404(userid)
        return None, 302, [('Location', user.avatar.url)]

    @expose_ajax('/<userid>/avatar/', methods=['PUT'])
    @check_authorization(self_auth=True)
    def set_avatar(self, userid):
        user = User.query.get_or_404(userid)
        user.avatar = process_image(User.avatar)
        user.save()
        return None, 204, [('Location', user.avatar.url)]

    @expose_ajax('/<userid>/activity/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_activity(self, userid):
        return user_activity(userid, self.get_locale(), self.get_page())

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
        # XXX: For now don't propogate activity to channel.
        # Saves db load and also there's the new set_channel_view_count cron command
        #channelid = VideoInstance.query.filter_by(id=form.video_instance.data).value('channel')
        #if channelid:
        #    save_channel_activity(userid, form.action.data, channelid, self.get_locale())

    @expose_ajax('/<userid>/notifications/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_notifications(self, userid):
        items, total = _notification_list(userid, self.get_page())
        return dict(notifications=dict(items=items, total=total))

    @expose_ajax('/<userid>/notifications/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_notifications(self, userid):
        try:
            notification_ids = map(int, request.json['mark_read'])
        except (TypeError, KeyError):
            abort(400, message=_('"mark_read" list parameter required'))
        except ValueError:
            abort(400, message=_('Invalid id list'))
        return _mark_read_notifications(userid, notification_ids)

    @expose_ajax('/<userid>/notifications/unread_count/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_notifications_unread_count(self, userid):
        return _notification_unread_count(userid)

    @expose_ajax('/<userid>/content_reports/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_content_report(self, userid):
        form = ContentReportForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)
        save_content_report(userid, form.object_type.data,
                            form.object_id.data, form.reason.data)

    @expose_ajax('/<userid>/channels/', cache_private=True)
    @check_authorization(self_auth=True)
    def get_channels(self, userid):
        return dict(channels=user_channels(userid, self.get_locale(), self.get_page()))

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
            cover_aoi=form.cover_aoi.data,
            category=form.category.data,
            public=form.public.data)
        return ajax_create_response(channel)

    @expose_ajax('/<userid>/channels/<channelid>/', cache_age=600, secure=False)
    def channel_info(self, userid, channelid):
        if use_elasticsearch():
            ch = api.ChannelSearch(self.get_locale())
            ch.add_id(channelid)
            ch.set_paging()
            size, limit = self.get_page()
            if not ch.channels(with_videos=True, with_owners=True, video_paging=(size, limit)):
                abort(404)
            return ch.channels()[0]

        channel = Channel.query.filter_by(id=channelid, public=True, deleted=False).first_or_404()
        return _channel_info_response(channel, self.get_locale(), self.get_page(), False)

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
        if not channel.editable:
            abort(400, message=_('Channel not editable'))
        form = ChannelForm(csrf_enabled=False, channelid=channelid)
        form.userid = userid
        if not form.validate():
            abort(400, form_errors=form.errors)

        channel.title = form.title.data
        channel.description = form.description.data
        if not form.cover.data == 'KEEP':
            channel.cover = form.cover.data
            channel.cover_aoi = form.cover_aoi.data
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
        if not channel.editable:
            abort(400, message=_('Channel not editable'))
        channel.deleted = True
        channel.save()

    @expose_ajax('/<userid>/channels/<channelid>/public/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def channel_public_toggle(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        if not channel.editable:
            abort(400, message=_('Channel not editable'))
        if not isinstance(request.json, bool):
            abort(400, message=_('Boolean value required'))
        intended_public = channel.should_be_public(channel, request.json)
        if channel.public != intended_public:
            channel.public = intended_public
            channel = channel.save()
        return channel.public

    @expose_ajax('/<userid>/channels/<channelid>/videos/', cache_age=600, secure=False)
    def channel_videos(self, userid, channelid):
        if use_elasticsearch():
            vs = api.VideoSearch(self.get_locale())
            vs.add_term('channel', [channelid])
            vs.add_sort('position', 'asc')
            vs.date_sort('desc')
            vs.add_sort('video.date_published', 'desc')
            vs.set_paging(*self.get_page())
            items = vs.videos()
            total = vs.total
        else:
            items, total = _channel_videos(channelid, self.get_locale(), self.get_page())
        return dict(videos=dict(items=items, total=total))

    @expose_ajax('/<userid>/channels/<channelid>/videos/', cache_age=0)
    @check_authorization()
    def owner_channel_videos(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if g.authorized.userid != userid and not channel.public:
            abort(404)
        items, total = _channel_videos(channelid, self.get_locale(), self.get_page(), own=True)
        return dict(videos=dict(items=items, total=total))

    @expose_ajax('/<userid>/channels/<channelid>/videos/', methods=('PUT', 'POST'))
    @check_authorization(self_auth=True)
    def update_channel_videos(self, userid, channelid):
        channel = Channel.query.filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        if request.json is None or not isinstance(request.json, list):
            abort(400, message=_('List can be empty, but must be present'))
        existing_videos = len(channel.video_instances)
        add_videos_to_channel(channel, request.json, self.get_locale(), request.method == 'PUT')

        intended_public = channel.should_be_public(channel, channel.public)
        if not channel.video_instances and not intended_public:
            channel.public = intended_public
            channel.save()
        elif not existing_videos and channel.should_be_public(channel, True):
            channel.public = True
            channel.save()

    @expose_ajax('/<userid>/channels/<channelid>/videos/<videoid>/')
    def channel_video_instance(self, userid, channelid, videoid):
        instance = VideoInstance.query.filter_by(id=videoid, channel=channelid).first_or_404()
        return video_api.video_dict(instance)

    @expose_ajax('/<userid>/channels/<channelid>/subscribers/', cache_age=600)
    def channel_subscribers(self, userid, channelid):
        items, total = _user_list(self.get_page(), subscribed_to=channelid)
        return dict(users=dict(items=items, total=total))

    @expose_ajax('/<userid>/cover_art/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_cover_art(self, userid):
        covers = UserCoverArt.query.filter_by(owner=userid).order_by(desc('date_created'))
        return cover_api.cover_art_response(covers, self.get_page(), own=True)

    @expose_ajax('/<userid>/cover_art/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_cover_art(self, userid):
        aoi = request.form.get('aoi')
        if aoi:
            try:
                aoi = get_box_value(aoi)
            except:
                abort(400, message=_('aoi must be of the form [x1, y1, x2, y2]'))
        path = process_image(UserCoverArt.cover)
        cover = UserCoverArt(cover=path, cover_aoi=aoi, owner=userid).save()
        return ajax_create_response(cover, cover_api.cover_art_dict(cover, own=True))

    @expose_ajax('/<userid>/cover_art/<ref>', cache_age=3600)
    def redirect_cover_art_item(self, userid, ref):
        cover = UserCoverArt.query.filter_by(cover=ref).first_or_404()
        return None, 302, [('Location', cover.cover.url)]

    @expose_ajax('/<userid>/cover_art/<ref>', methods=['DELETE'])
    @check_authorization(self_auth=True)
    @commit_on_success
    def delete_cover_art_item(self, userid, ref):
        if not UserCoverArt.query.filter_by(cover=ref).delete():
            abort(404)

    @expose_ajax('/<userid>/subscriptions/')
    def get_subscriptions(self, userid):
        return dict(channels=user_subscriptions(userid, self.get_locale(), self.get_page()))

    @expose_ajax('/<userid>/subscriptions/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_subscriptions(self, userid):
        endpoint, args = url_to_endpoint(request.json or '')
        if endpoint not in ('userws.owner_channel_info', 'userws.channel_info'):
            abort(400, message=_('Invalid channel url'))
        channelid = args['channelid']
        if not Channel.query.filter_by(id=channelid, deleted=False).count():
            abort(400, message=_('Channel not found'))
        if Subscription.query.filter_by(user=userid, channel=channelid).count():
            abort(400, message=_('Already subscribed'))
        subs = Subscription(user=userid, channel=channelid).save()
        save_channel_activity(userid, 'subscribe', channelid, self.get_locale())
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
        if not _user_subscriptions_query(userid).filter_by(channel=channelid).delete():
            abort(404)
        save_channel_activity(userid, 'unsubscribe', channelid, self.get_locale())

    @expose_ajax('/<userid>/subscriptions/recent_videos/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def recent_videos(self, userid):
        channels = [
            s[0] for s in _user_subscriptions_query(userid).join(Channel).
            filter_by(public=True, deleted=False).values('channel')]
        if channels:
            items, total = video_api.get_local_videos(self.get_locale(), self.get_page(),
                                                      date_order=True, channels=channels, readonly_db=True)
        else:
            items, total = [], 0
        return dict(videos=dict(items=items, total=total))

    @expose_ajax('/<userid>/external_accounts/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_external_accounts(self, userid):
        return dict(external_accounts=user_external_accounts(userid, self.get_locale(), self.get_page()))

    @expose_ajax('/<userid>/external_accounts/<id>/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_external_account(self, userid, id):
        token = ExternalToken.query.filter_by(user=userid, id=id).first_or_404()
        return dict(external_system=token.external_system, external_uid=token.external_uid)

    @expose_ajax('/<userid>/external_accounts/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_external_accounts(self, userid):
        eu = external_user_from_token_form()
        token = ExternalToken.update_token(userid, eu)
        record_user_event(str(userid), '%s token updated' % eu.system, userid)
        return ajax_create_response(token)

    @expose_ajax('/<userid>/friends/', cache_age=600, cache_private=True)
    @check_authorization(self_auth=True)
    def get_friends(self, userid):
        ExternalFriend.populate_facebook_friends(userid)
        friends = ExternalFriend.query.filter_by(user=userid).all()
        rockpack_friends = dict(
            (user.external_tokens[0].external_uid, user)
            for user in User.query.join(ExternalToken, (
                (ExternalToken.user == User.id) &
                (ExternalToken.external_system == 'facebook') &
                (ExternalToken.external_uid.in_(set(f.external_uid for f in friends)))
            )).options(contains_eager(User.external_tokens)).order_by('date_joined desc')
        )
        items = []
        for friend in friends:
            rockpack_user = rockpack_friends.get(friend.external_uid)
            if rockpack_user:
                item = dict(
                    id=rockpack_user.id,
                    resource_url=rockpack_user.get_resource_url(),
                    display_name=rockpack_user.display_name,
                    avatar_thumbnail_url=rockpack_user.avatar.url,
                )
            else:
                item = dict(
                    display_name=friend.name,
                    avatar_thumbnail_url=friend.avatar_url,
                    external_uid=friend.external_uid,
                    external_system=friend.external_system,
                )
            if friend.has_ios_device:
                item['has_ios_device'] = True
            items.append(item)
        if 'ios' in request.args.get('device_filter', ''):
            items = [i for i in items if 'resource_url' in i or 'has_ios_device' in i]
        items.sort(key=lambda i: i['display_name'])
        for i, item in enumerate(items):
            item['position'] = i
        return dict(users=dict(items=items, total=len(items)))

    @expose_ajax('/<userid>/friends/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_friends(self, userid):
        # placeholder
        abort(501)
