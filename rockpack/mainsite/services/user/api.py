from itertools import groupby
from functools import partial
from werkzeug.datastructures import MultiDict
from sqlalchemy import desc, func, text
from sqlalchemy.orm import lazyload, contains_eager
from sqlalchemy.orm.exc import NoResultFound
from flask import abort, request, json, g
from flask.ext import wtf
from flask.ext.admin import form
from rockpack.mainsite.core.apns import push_client
from wtforms.validators import ValidationError
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.webservice import WebService, expose_ajax, ajax_create_response, process_image
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.core.youtube import get_video_data
from rockpack.mainsite.core.es import use_elasticsearch, search as es_search
from rockpack.mainsite.core.es.api import es_update_channel_videos
from rockpack.mainsite.core import recommender
from rockpack.mainsite.helpers import lazy_gettext as _
from rockpack.mainsite.helpers.forms import naughty_word_validator
from rockpack.mainsite.helpers.urls import url_for, url_to_endpoint
from rockpack.mainsite.helpers.db import gen_videoid, get_column_validators, get_box_value
from rockpack.mainsite.services.video.models import (
    Channel, ChannelLocaleMeta, Video, VideoInstance, VideoInstanceLocaleMeta, Category, ContentReport)
from rockpack.mainsite.services.oauth.api import (
    RockRegistrationForm, ExternalTokenManager, ExternalRegistrationForm, record_user_event)
from rockpack.mainsite.services.oauth.models import ExternalFriend, ExternalToken
from rockpack.mainsite.services.cover_art.models import UserCoverArt, RockpackCoverArt
from rockpack.mainsite.services.cover_art import api as cover_api
from rockpack.mainsite.services.video import api as video_api
from rockpack.mainsite.services.search import api as search_api
from .models import (
    User, UserActivity, UserContentFeed, UserNotification, UserInterest,
    Subscription, UserFlag, USER_FLAGS)


ACTION_COLUMN_VALUE_MAP = dict(
    open=('view_count', 1),
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

SUBSCRIPTION_VIDEO_FEED_THRESHOLD = func.now() - text("interval '1 day'")


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
        existing_ids = dict((i, (v, c)) for i, v, c in instances.values('id', 'video', 'channel'))
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
            existing_ids[(source, source_videoid)] = (video_id, None)

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

    video_id = get_or_create_video_records([instance_id])[0][0]
    activity = dict(user=userid, action=action,
                    object_type='video_instance', object_id=instance_id, locale=locale)
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

    activity.update(tracking_code=request.args.get('tracking_code'))
    UserActivity(**activity).add()

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
    updated = Channel.query.filter_by(id=channelid).update(incr(Channel))
    if not updated:
        return
    # Update or create locale meta record:
    ChannelLocaleMeta.query.filter_by(channel=channelid, locale=locale).update(incr(ChannelLocaleMeta)) or \
        ChannelLocaleMeta(channel=channelid, locale=locale, **{column: value}).add()
    if action in ('subscribe', 'unsubscribe', 'open'):
        UserActivity(
            user=userid,
            action=action,
            object_type='channel',
            object_id=channelid,
            tracking_code=request.args.get('tracking_code'),
        ).add()
    if app.config['MYRRIX_URL'] and action == 'open':
        recommender.record_activity(userid, channelid)


@commit_on_success
def save_content_report(userid, object_type, object_id, reason):
    activity = dict(action='content_reported', user=userid,
                    object_type=object_type, object_id=object_id)
    if not UserActivity.query.filter_by(**activity).count():
        activity.update(tracking_code=request.args.get('tracking_code'))
        UserActivity(**activity).add()
    report = dict(object_type=object_type, object_id=object_id, reason=reason)
    updated = ContentReport.query.filter_by(**report).update(
        {ContentReport.count: ContentReport.count + 1})
    if not updated:
        report = ContentReport(**report).add()


@commit_on_success
def add_videos_to_channel(channel, instance_list, locale, delete_existing=False):
    videomap = get_or_create_video_records(instance_list)
    existing = dict((v.video, v) for v in
                    VideoInstance.query.filter_by(channel=channel.id).options(lazyload('video_rel')))
    added = []
    for position, (video_id, video_source) in enumerate(videomap):
        if video_id not in added:
            instance = existing.get(video_id) or \
                VideoInstance(video=video_id, channel=channel.id, source_channel=video_source)
            instance.position = position
            VideoInstance.query.session.add(instance)
            added.append(video_id)

    deleted_video_ids = []
    if delete_existing:
        deleted_video_ids = set(existing.keys()).difference([i for i, s in videomap])
        if deleted_video_ids:
            channel.remove_videos(deleted_video_ids)

    # Set to private if videos are cleared, or public if first videos added
    if delete_existing and not added:
        channel.public = False
    elif not existing and Channel.should_be_public(channel, True, added):
        channel.public = True


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


def _apns_mark_unread(userid):
    try:
        device = ExternalToken.query.filter(
            ExternalToken.external_system == 'apns',
            ExternalToken.external_token != 'INVALID',
            ExternalToken.user == userid).one()
    except NoResultFound:
        pass
    else:
        try:
            message = push_client.Message(
                device.external_token,
                alert={},
                badge=0)

            srv = push_client.APNs(push_client.connection)
            srv.send(message)
        except Exception, e:
            app.logger.error('Failed to send push notification: %s', str(e))


@commit_on_success
def _mark_read_notifications(userid, id_list):
    unread = UserNotification.query.filter_by(user=userid, date_read=None)
    unread_count = unread.count()
    marked_read = unread.filter(
        UserNotification.id.in_(id_list)
    ).update({UserNotification.date_read: func.now()}, False)

    if marked_read and marked_read == unread_count:
        _apns_mark_unread(userid)


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
    items, total = video_api.get_db_channels(locale, paging, channels=subs.keys())
    items = [item for date, item in
             sorted([(subs[i['id']], i) for i in items], reverse=True)]
    for item in items:
        item['subscription_resource_url'] =\
            url_for('userws.delete_subscription_item', userid=userid, channelid=item['id'])
    return dict(items=items, total=total)


def user_channels(userid, locale, paging, tracking_prefix='ownprofile'):
    channels = Channel.query.options(lazyload('owner_rel'), lazyload('category_rel')).\
        filter_by(owner=userid, deleted=False)
    total = channels.count()
    offset, limit = paging
    channels = channels.order_by('favourite desc', 'date_added desc').\
        offset(offset).limit(limit)
    items = [video_api.channel_dict(c, p, with_owner=False, owner_url=True,
                                    add_tracking=partial(_add_tracking, prefix=tracking_prefix))
             for p, c in enumerate(channels)]
    return dict(items=items, total=total)


def user_external_accounts(userid, locale, paging):
    items = []
    for token in ExternalToken.query.filter_by(user=userid):
        items.append(dict(resource_url=token.resource_url,
                          external_system=token.external_system,
                          external_token=token.external_token,
                          external_uid=token.external_uid,
                          token_expires=token.expires and token.expires.isoformat(),
                          token_permissions=token.permissions,
                          meta=token.meta))
    return dict(items=items, total=len(items))


def user_activity(userid, locale, paging):
    ids = dict((key, action_object_list(userid, key, UserWS.max_page_size))
               for key in ACTION_COLUMN_VALUE_MAP)
    return dict(
        recently_viewed=ids['view'],
        recently_starred=list(set(ids['star']) - set(ids['unstar'])),
        subscribed=list(set(ids['subscribe']) - set(ids['unsubscribe'])),
    )


def user_flags(userid, locale, paging):
    items = [dict(flag=f.flag, resource_url=f.resource_url)
             for f in UserFlag.query.filter_by(user=userid)]
    return dict(items=items, total=len(items))


def set_user_flag(userid, flag):
    if flag not in USER_FLAGS:
        abort(400, message=_('Invalid user flag.'))
    user = User.query.get_or_404(userid)
    userflag = user.set_flag(flag)
    user.save()
    return userflag and ajax_create_response(userflag, dict(id=flag))


def check_present(form, field):
    if field.name not in (request.json or request.form):
        raise ValidationError(_('This field is required, but can be an empty string.'))


def _add_tracking(item, prefix=None):
    item['tracking_code'] = ' '.join(filter(None, map(str, [prefix, item.get('position')])))


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
    video_instance = wtf.StringField()  # XXX: needed for backwards compatibility
    object_type = wtf.SelectField(choices=ACTIVITY_OBJECT_TYPE_MAP.items(), validators=[wtf.Optional()])
    object_id = wtf.StringField()

    def validate(self):
        success = super(ActivityForm, self).validate()
        # check that either video_instance or object_type/object_id is provided
        if self.video_instance.data:
            self.object_type.data = 'video_instance'
            self.object_id.data = self.video_instance.data
        else:
            if not self.object_id.data:
                self._errors = dict([
                    (f, _('This field is required.')) for f in 'object_type', 'object_id'])
                success = False
        return success


class ContentReportForm(wtf.Form):
    object_type = wtf.SelectField(choices=ACTIVITY_OBJECT_TYPE_MAP.items())
    object_id = wtf.StringField(validators=[wtf.Required()])
    reason = wtf.StringField(validators=get_column_validators(ContentReport, 'reason'))

    def validate_object_id(self, field):
        object_type = ACTIVITY_OBJECT_TYPE_MAP.get(self.object_type.data)
        if object_type and not object_type.query.filter_by(id=field.data).count():
            raise ValidationError(_('Invalid id.'))


def _content_feed(userid, locale, paging, country=None):
    feed = UserContentFeed.query.filter_by(user=userid)
    total = feed.count()
    offset, limit = paging
    feed = feed.order_by('date_added desc').offset(offset).limit(limit)
    itemmap, videomap, channelmap = dict(), dict(), dict()
    count = 0
    for i, item in enumerate(feed):
        count += 1
        if item.video_instance:
            videomap[item.video_instance] = None
            itemmap[item.video_instance] = i, item
        else:
            channelmap[item.channel] = None
            itemmap[item.channel] = i, item
    items = [None] * count
    if count == 0:
        return items, total
    usermap = dict()

    # Get video data
    vs = es_search.VideoSearch(locale)
    vs.check_country_allowed(country)
    vs.set_paging(0, -1)
    vs.add_id(videomap.keys())
    for video in vs.videos(with_stars=True):
        i, item = itemmap[video['id']]
        # Compose list of liking users from feed item and global video stars
        item._starring_users = json.loads(item.stars) if item.stars else []
        for user in video.pop('recent_user_stars'):
            if user not in item._starring_users:
                item._starring_users.append(user)
        usermap.update((u, None) for u in item._starring_users)
        channelmap[item.channel] = None
        video['position'] = i + offset
        video['tracking_code'] = 'feed %d video' % (i + offset)
        items[i] = video

    # Get channel data - for both feed channel items and video items
    cs = es_search.ChannelSearch(locale)
    cs.set_paging(0, -1)
    cs.add_id(channelmap.keys())
    for channel in cs.channels():
        usermap[channel['owner']] = None
        channelmap[channel['id']] = channel
        if channel['id'] in itemmap:
            i, item = itemmap[channel['id']]
            channel['position'] = i + offset
            channel['tracking_code'] = 'feed %d channel' % (i + offset)
            items[i] = channel
        else:
            channel.pop('position')

    # Get user data for channel owners and stars list
    us = es_search.UserSearch()
    us.set_paging(0, -1)
    us.add_id(usermap.keys())
    for user in us.users():
        user.pop('position')
        usermap[user['id']] = user

    # Add owner data to channels
    for channel in channelmap.values():
        if channel:
            channel['owner'] = usermap[channel['owner']]

    # Add channel & user star data to videos
    star_limit = app.config.get('FEED_STARS_LIMIT', 3)
    for videoid in videomap.keys():
        i, item = itemmap[videoid]
        channel = channelmap.get(item.channel)
        if items[i] and channel:
            items[i]['channel'] = channel
            if item._starring_users:
                # star_count could possibly be out of sync so ensure it's value isn't too surprising
                items[i]['video']['star_count'] = max(
                    items[i]['video']['star_count'], len(item._starring_users))
                items[i]['starring_users'] =\
                    [usermap[u] for u in item._starring_users if usermap[u]][:star_limit]
        else:
            # Perhaps channel is no longer public?
            items[i] = None

    return filter(None, items), total


def _aggregate_content_feed(items):
    # First group all items by key
    itemgroups = {}
    for item in items:
        if 'channel' in item:
            key = 'video', item['channel']['id'], item['date_added'][:10]   # same channel and day
        else:
            key = 'channel', item['owner']['id'], item['date_published'][:8]  # same owner and week
        itemgroups.setdefault(key, []).append(item)

    # Then summarise aggregations from selected groups
    aggregations = {}
    for (type, key, date), group in itemgroups.iteritems():
        if type == 'video':
            # Don't create small aggregations for videos
            if len(group) <= 5:
                continue
            # Don't include most starred videos (up to a maximum of 5)
            group.sort(key=lambda i: i['video']['star_count'], reverse=True)
            x, count = 0, len(group)
            while x < min(10, count) and group[x].get('starring_users'):
                x += 1
            group = group[x:]

        count = len(group)
        if count <= 1:
            continue

        aggid = str(group[0]['position'])
        aggregations[aggid] = dict(
            type=type,
            count=count,
            covers=[item['id'] for item in group[:4 if type == 'channel' else 1]],
        )
        for item in group:
            item['aggregation'] = aggid

    return aggregations


def _normalise_boosts(boosts, limit):
    # normalise the positive boosts so that the max boost factor is at the limit
    limit = limit - 1   # 1 is added back later
    pos_boosts = [b for c, b in boosts if b > 1]
    bmin, bmax = min(pos_boosts), max(pos_boosts)
    if bmin == bmax:
        return boosts
    else:
        return [(k, 1 + (limit * (b - bmin) / (bmax - bmin)) if b > 1 else b)
                for k, b in boosts]


def _channel_recommendations(userid, locale, paging):
    interests = list(UserInterest.query.filter_by(user=userid, explicit=False).
                     order_by('weight desc').limit(5).values('category', 'weight'))
    if interests:
        boostfactor = app.config.get('RECOMMENDER_INTEREST_BOOST_FACTOR', 1.4)
        d = boostfactor / interests[0][1]
        cat_boosts = [(c, i * d) for c, i in interests]
    else:
        cat_boosts = []

    demo_boosts = app.config['RECOMMENDER_CATEGORY_BOOSTS']
    (gender, age), = User.query.filter_by(id=userid).values(
        User.gender, func.age(User.date_of_birth))
    if gender:
        cat_boosts.extend(demo_boosts['gender'][gender])
    if age:
        age = age.days / 365
        cat_boosts.extend(next(
            (v for k, v in sorted(demo_boosts['age'].items()) if age < k), ()))

    # combine boosts by multiplying each with the same category
    cat_boosts = [(i, reduce(lambda a, b: a * b[1], grp, 1))
                  for i, grp in groupby(sorted(cat_boosts), lambda x: x[0])]
    if cat_boosts:
        cat_boosts = _normalise_boosts(
            cat_boosts, app.config.get('RECOMMENDER_CATEGORY_BOOST_LIMIT', 1.8))

    prefix_boosts = None
    if app.config['MYRRIX_URL']:
        try:
            channel_recs = recommender.get_channel_recommendations(userid)
        except:
            app.logger.exception('Unable to get recommendations for %s', userid)
        else:
            prefix_boosts = _normalise_boosts(
                [('ch' + c, 1 + w) for c, w in channel_recs],
                app.config.get('RECOMMENDER_CATEGORY_BOOST_LIMIT', 5.0))

    cat_boost_map = dict(cat_boosts)
    prefix_boost_map = dict(prefix_boosts or ())

    def add_tracking(channel):
        extra_tracking = []
        cat = channel.get('category')
        if cat in cat_boost_map:
            extra_tracking.append('cat-%d-%.2f' % (cat, cat_boost_map[cat]))
        prefix = channel['id'][:12]
        if prefix in prefix_boost_map:
            extra_tracking.append('rec-%.2f' % prefix_boost_map[prefix])
        channel['tracking_code'] = ' '.join(['rec', str(channel['position'])] + extra_tracking)

    return video_api.get_es_channels(
        locale, paging, None, cat_boosts, prefix_boosts, add_tracking, enable_promotion=False)


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
        add_tracking = partial(_add_tracking, prefix='profile')
        if use_elasticsearch():
            us = es_search.UserSearch()
            us.add_id(userid)
            owners = us.users()
            if not owners:
                abort(404)
            owner = owners[0]
            ch = es_search.ChannelSearch(self.get_locale())
            offset, limit = self.get_page()
            ch.set_paging(offset, limit)
            ch.favourite_sort('desc')
            ch.add_sort('date_updated')
            ch.add_term('owner', userid)
            owner.setdefault('channels', {})['items'] =\
                ch.channels(with_owners=False, add_tracking=add_tracking)
            owner['channels']['total'] = ch.total
            return owner

        user = User.query.get_or_404(userid)
        channels = [video_api.channel_dict(c, p, owner_url=False,
                                           with_owner=False, add_tracking=add_tracking)
                    for p, c in enumerate(Channel.query.options(lazyload('category_rel')).
                    filter_by(owner=user.id, deleted=False, public=True).
                    order_by('favourite desc', 'channel.date_updated desc'))]

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
                    'friends', 'external_accounts', 'flags'):
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

    @expose_ajax('/<userid>/flags/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_flags(self, userid):
        return user_flags(userid, self.get_locale(), self.get_page())

    @expose_ajax('/<userid>/flags/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_flags(self, userid):
        return set_user_flag(userid, request.form['flag'])

    @expose_ajax('/<userid>/flags/<flag>/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_flag_item(self, userid, flag):
        if flag not in USER_FLAGS:
            abort(400, message=_('Invalid user flag.'))
        return bool(UserFlag.query.filter_by(user=userid, flag=flag).first_or_404())

    @expose_ajax('/<userid>/flags/<flag>/', methods=['PUT'])
    @check_authorization(self_auth=True)
    def put_flag_item(self, userid, flag):
        return set_user_flag(userid, flag)

    @expose_ajax('/<userid>/flags/<flag>/', methods=['DELETE'])
    @check_authorization(self_auth=True)
    def delete_flag_item(self, userid, flag):
        user = User.query.get_or_404(userid)
        user.unset_flag(flag)
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
        return dict(thumbnail_url=user.avatar.url), 200, [('Location', user.avatar.url)]

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
        if form.object_type.data == 'channel':
            save_channel_activity(
                userid, form.action.data, form.object_id.data, self.get_locale())
        else:
            save_video_activity(
                userid, form.action.data, form.object_id.data, self.get_locale())

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
            ch = es_search.ChannelSearch(self.get_locale())
            ch.add_id(channelid)
            location = request.args.get('location')
            if location:
                ch.check_country_allowed(location.upper())
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

        channel_was_public = channel.public

        channel.title = form.title.data
        channel.description = form.description.data
        if not form.cover.data == 'KEEP':
            channel.cover = form.cover.data
            channel.cover_aoi = form.cover_aoi.data
        channel.category = form.category.data
        channel.public = Channel.should_be_public(channel, form.public.data)
        channel.save()

        # Push all videos to search if channel became public:
        if channel.public and not channel_was_public:
            es_update_channel_videos(
                v[0] for v in VideoInstance.query.filter_by(channel=channel.id).values('id'))

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
        intended_public = Channel.should_be_public(channel, request.json)
        if channel.public != intended_public:
            channel.public = intended_public
            channel = channel.save()
        return channel.public

    @expose_ajax('/<userid>/channels/<channelid>/videos/', cache_age=600, secure=False)
    def channel_videos(self, userid, channelid):
        if use_elasticsearch():
            location = request.args.get('location')
            vs = es_search.VideoSearch(self.get_locale())
            vs.add_term('channel', [channelid])
            if location:
                vs.check_country_allowed(location.upper())
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
        channel = Channel.query.options(lazyload('owner_rel'), lazyload('category_rel')).\
            filter_by(id=channelid, deleted=False).first_or_404()
        if not channel.owner == userid:
            abort(403)
        if request.json is None or not isinstance(request.json, list):
            abort(400, message=_('List can be empty, but must be present'))

        add_videos_to_channel(channel, request.json, self.get_locale(),
                              request.method == 'PUT')

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
        # Add some recent videos from this channel into the users feed
        UserContentFeed.query.session.add_all(
            UserContentFeed(user=userid, channel=channelid, video_instance=id, date_added=date_added)
            for id, date_added in VideoInstance.query.filter_by(channel=channelid).
            filter(VideoInstance.date_added > SUBSCRIPTION_VIDEO_FEED_THRESHOLD).
            limit(10).values('id', 'date_added'))
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
        # Remove any videos from this channel from the users feed
        UserContentFeed.query.filter_by(user=userid, channel=channelid).delete()
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

    @expose_ajax('/<userid>/content_feed/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def content_feed(self, userid):
        items, total = _content_feed(userid, self.get_locale(), self.get_page())
        aggregations = _aggregate_content_feed(items) if items else {}
        return dict(content=dict(items=items, total=total, aggregations=aggregations))

    @expose_ajax('/<userid>/channel_recommendations/', cache_age=3600, cache_private=True)
    @check_authorization(self_auth=True)
    def channel_recommendations(self, userid):
        items, total = _channel_recommendations(userid, self.get_locale(), self.get_page())
        return dict(channels=dict(items=items, total=total))

    @expose_ajax('/<userid>/external_accounts/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_external_accounts(self, userid):
        return dict(external_accounts=user_external_accounts(userid, self.get_locale(), self.get_page()))

    @expose_ajax('/<userid>/external_accounts/<id>/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_external_account(self, userid, id):
        token = ExternalToken.query.filter_by(user=userid, id=id).first_or_404()
        return dict(external_system=token.external_system, external_uid=token.external_uid)

    @expose_ajax('/<userid>/external_accounts/<id>/', methods=['DELETE'])
    @check_authorization(self_auth=True)
    @commit_on_success
    def delete_external_account(self, userid, id):
        if not ExternalToken.query.filter_by(user=userid, id=id).delete():
            abort(404)

    @expose_ajax('/<userid>/external_accounts/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_external_accounts(self, userid):
        form = ExternalRegistrationForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)

        eu = ExternalTokenManager(**form.data)
        if not eu.token_is_valid:
            abort(400, error='unauthorized_client')

        token = ExternalToken.update_token(userid, eu)
        record_user_event(str(userid), '%s token updated' % eu.system, userid=userid)
        return None if hasattr(token, '_existing') else ajax_create_response(token)

    @expose_ajax('/<userid>/friends/', cache_age=600, cache_private=True)
    @check_authorization(self_auth=True)
    def get_friends(self, userid):
        if request.args.get('share_filter'):
            friends = ExternalFriend.query.filter_by(user=userid).filter(
                ExternalFriend.last_shared_date.isnot(None))
        else:
            ExternalFriend.populate_facebook_friends(userid)
            friends = ExternalFriend.query.filter_by(user=userid)
        friends = friends.all()
        rockpack_friends = dict(
            (('facebook', user.external_tokens[0].external_uid), user)
            for user in User.query.join(ExternalToken, (
                (ExternalToken.user == User.id) &
                (ExternalToken.external_system == 'facebook') &
                (ExternalToken.external_uid.in_(
                    set(f.external_uid for f in friends if f.external_system == 'facebook')))
            )).options(contains_eager(User.external_tokens))
        )
        rockpack_friends.update(
            (('email', user.email), user)
            for user in User.query.filter(
                User.email.in_(set(f.email for f in friends if f.external_system == 'email')))
        )
        items = []
        for friend in friends:
            uid = friend.email if friend.external_system == 'email' else friend.external_uid
            rockpack_user = rockpack_friends.get((friend.external_system, uid))
            last_shared_date = friend.last_shared_date and friend.last_shared_date.isoformat()
            item = dict(
                display_name=friend.name,
                avatar_thumbnail_url=friend.avatar_url,
                external_uid=friend.external_uid,
                external_system=friend.external_system,
                email=friend.email,
                last_shared_date=last_shared_date,
            )
            if rockpack_user:
                item.update(
                    id=rockpack_user.id,
                    resource_url=rockpack_user.get_resource_url(),
                    display_name=rockpack_user.display_name,
                    avatar_thumbnail_url=rockpack_user.avatar.url,
                    email=rockpack_user.email or friend.email,
                )
            if friend.has_ios_device:
                item.update(
                    has_ios_device=True,
                )
            items.append(item)
        if 'ios' in request.args.get('device_filter', ''):
            items = [i for i in items if 'resource_url' in i or 'has_ios_device' in i]
        if request.args.get('share_filter'):
            items.sort(key=lambda i: i['last_shared_date'], reverse=True)
        else:
            items.sort(key=lambda i: i['display_name'])
        for i, item in enumerate(items):
            item['position'] = i
        return dict(users=dict(items=items, total=len(items)))

    @expose_ajax('/<userid>/friends/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_friends(self, userid):
        # placeholder
        abort(501)
