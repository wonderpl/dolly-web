from datetime import datetime, timedelta
import wtforms as wtf
from flask import request, abort
from flask.ext.wtf import Form
import pyes
from collections import defaultdict
from sqlalchemy import func, null
from sqlalchemy.orm import contains_eager, lazyload
from sqlalchemy.sql.expression import desc
from sqlalchemy.orm.exc import NoResultFound
from rockpack.mainsite import app
from rockpack.mainsite.core import ooyala
from rockpack.mainsite.core.dbapi import readonly_session, db, commit_on_success
from rockpack.mainsite.core.webservice import WebService, expose_ajax, secure_view
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.core.es import use_elasticsearch, filters
from rockpack.mainsite.core.es.search import VideoSearch, ChannelSearch
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.user.models import User


def _filter_by_category(query, type, category_id):
    """Filter given query by the specified category.
    If top-level category given, then filter by all sub categories.
    """
    sub_cats = list(models.Category.query.filter_by(parent=category_id).
                    values(models.Category.id))
    cat_ids = zip(*sub_cats)[0] if sub_cats else [category_id]
    return query.filter(type.category.in_(cat_ids))


def user_dict(user, own=False):
    return dict(
        id=user.id,
        resource_url=user.get_resource_url(own),
        display_name=user.display_name,
        avatar_thumbnail_url=user.avatar.thumbnail_medium,
    )


def channel_dict(channel, position=None, with_owner=True, owner_url=False, video_count=None, add_tracking=None):
    ch_data = dict(
        id=channel.id,
        resource_url=channel.get_resource_url(owner_url),
        title=channel.title,
        description=channel.description,
        subscriber_count=channel.subscriber_count,
        category=channel.category,
        date_published=channel.date_published and channel.date_published.isoformat(),
        cover=dict(
            thumbnail_url=channel.cover.url,
            aoi=channel.cover_aoi,
        )
    )
    if channel.favourite:
        if channel.title == 'Watch Later':
            ch_data['watchlater'] = True
        else:
            ch_data['favourites'] = True
    if channel.verified:
        ch_data['verified'] = True
    if with_owner:
        ch_data['owner'] = user_dict(channel.owner_rel, own=owner_url)
    if owner_url:
        ch_data['public'] = channel.public
    if position is not None:
        ch_data['position'] = position
    if video_count is not None:
        ch_data['videos'] = dict(total=video_count)
    if app.config.get('SHOW_OLD_CHANNEL_COVER_URLS', True):
        for k in 'thumbnail_large', 'thumbnail_small', 'background':
            ch_data['cover_%s_url' % k] = getattr(channel.cover, k)
    if add_tracking:
        add_tracking(ch_data)
    return ch_data


def get_db_channels(locale, paging, with_video_counts=False, add_tracking=None, **filters):
    channels = models.Channel.query.filter_by(public=True, deleted=False).\
        join(models.User).\
        outerjoin(
            models.ChannelLocaleMeta,
            ((models.ChannelLocaleMeta.channel == models.Channel.id) &
             (models.ChannelLocaleMeta.locale == locale))).\
        options(lazyload('category_rel'), contains_eager(models.Channel.owner_rel))

    if filters.get('channels'):
        channels = channels.filter(models.Channel.id.in_(filters['channels']))
    if filters.get('category'):
        channels = _filter_by_category(channels, models.Channel, filters['category'])
    if filters.get('query'):
        channels = channels.filter(func.lower(models.Channel.title).
                                   like('%%%s%%' % filters['query'].lower()))

    if filters.get('date_order'):
        channels = channels.order_by(desc(models.Channel.date_added))

    if with_video_counts:
        channels = channels.outerjoin(
            models.VideoInstance,
            (models.VideoInstance.channel == models.Channel.id) &
            (models.VideoInstance.deleted == False)
        ).with_entities(models.Channel, func.count(models.VideoInstance.id)).\
            group_by(models.Channel.id, models.User.id)
    else:
        channels = channels.with_entities(models.Channel, null())

    total = channels.count()
    offset, limit = paging
    items = [
        channel_dict(channel, position,
                     video_count=video_count,
                     add_tracking=add_tracking)
        for position, (channel, video_count) in
        enumerate(channels.offset(offset).limit(limit), offset)
    ]

    return items, total


def get_es_channels(locale, paging, category, category_boosts=None,
                    prefix_boosts=None, add_tracking=None, enable_promotion=True):
    cs = ChannelSearch(locale)
    cs.set_paging(*paging)
    # Boost popular channels based on ...
    if category_boosts:
        for boost in category_boosts:
            cs.add_filter(filters.category_boost(*boost))
    if prefix_boosts:
        for boost in prefix_boosts:
            cs.add_filter(filters.channel_prefix_boost(*boost))
    cs.add_filter(filters.boost_from_field_value('editorial_boost'))
    cs.add_filter(filters.negatively_boost_favourites())
    cs.add_filter(filters.channel_rank_boost(locale))
    cs.filter_category(category)
    if enable_promotion:
        cs.promotion_settings(category)
    cs.date_sort(request.args.get('date_order'))
    if request.args.get('user_id'):
        cs.add_term('owner', request.args.get('user_id'))
    channels = cs.channels(with_owners=True, add_tracking=add_tracking)
    return channels, cs.total


def video_dict(instance):
    video = instance.video_rel
    data = dict(
        id=instance.id,
        title=video.title,
        label=instance.label,
        date_added=instance.date_added.isoformat(),
        video=dict(
            id=video.id,
            source=models.Source.id_to_label(video.source),
            source_id=video.source_videoid,
            source_username=video.source_username,
            duration=video.duration,
            view_count=video.view_count,
            star_count=video.star_count,
            thumbnail_url=video.default_thumbnail,
            description=models.Video.cleaned_description(video.description),
            link_url=video.link_url,
            link_title=video.link_title
        )
    )

    data['video'].update(models.Video.extra_meta(video))

    original_channel_owner = instance.get_original_channel_owner()
    if original_channel_owner:
        data['original_channel_owner'] = user_dict(original_channel_owner)
    return data


def get_local_videos(loc, paging, with_channel=True, with_comments=False, include_invisible=False,
                     readonly_db=False, add_tracking=None, **filters):
    session = readonly_session if readonly_db else db.session
    videos = session.query(
        models.VideoInstance,
        func.count(models.VideoInstanceComment.id) if with_comments else null(),
    ).join(
        models.Video, models.Video.id == models.VideoInstance.video).\
        filter(models.VideoInstance.deleted == False).\
        options(contains_eager(models.VideoInstance.video_rel)).\
        group_by(models.VideoInstance.id, models.Video.id)

    if with_comments:
        videos = videos.outerjoin(
            models.VideoInstanceComment,
            models.VideoInstanceComment.video_instance == models.VideoInstance.id)

    if include_invisible is False:
        videos = videos.filter(models.Video.visible == True)
    if with_channel:
        videos = videos.join(
            models.Channel,
            models.Channel.id == models.VideoInstance.channel
        ).options(lazyload(
            models.VideoInstance.video_channel,
            models.Channel.category_rel))

    if filters.get('channel'):
        filters.setdefault('channels', [filters['channel']])

    if filters.get('channels'):
        videos = videos.filter(models.VideoInstance.channel.in_(filters['channels']))

    if filters.get('owner'):
        # Check we haven't already joined Channel
        if not with_channel:
            videos = videos.join(
                models.Channel,
                models.Channel.id == models.VideoInstance.channel)
        videos = videos.filter(models.Channel.owner == filters['owner'])

    if filters.get('category'):
        videos = _filter_by_category(videos, models.VideoInstance, filters['category'][0])

    if filters.get('position_order'):
        videos = videos.order_by(models.VideoInstance.position)

    if filters.get('star_order'):
        videos = videos.outerjoin(
            models.VideoInstanceLocaleMeta,
            (models.VideoInstanceLocaleMeta.video_instance == models.VideoInstance.id) &
            (models.VideoInstanceLocaleMeta.locale == loc))
        videos = videos.group_by(models.VideoInstance.id, models.Video.id, models.VideoInstanceLocaleMeta.star_count).\
            order_by(desc(models.VideoInstanceLocaleMeta.star_count))

    if filters.get('date_order'):
        videos = videos.order_by(desc(models.VideoInstance.date_added)).\
            order_by(desc(models.Video.date_published))

    total = videos.count()
    offset, limit = paging
    videos = videos.offset(offset).limit(limit)
    data = []
    for position, (video, comment_count) in enumerate(videos, offset):
        item = video_dict(video)
        item['position'] = position
        if comment_count is not None:
            item['comments'] = dict(count=comment_count)
        if with_channel:
            item['channel'] = channel_dict(video.video_channel)
        if add_tracking:
            add_tracking(item)
        data.append(item)
    return data, total


@commit_on_success
def save_player_error(video_instance, reason):
    report = dict(video_instance=video_instance, reason=reason)
    updated = models.PlayerErrorReport.query.filter_by(**report).update(
        {models.PlayerErrorReport.count: models.PlayerErrorReport.count + 1})
    if not updated:
        report = models.PlayerErrorReport(**report).save()


class PlayerErrorForm(Form):
    error = wtf.StringField(validators=[wtf.validators.Required()])
    video_instance = wtf.StringField(validators=[wtf.validators.Required()])


class VideoWS(WebService):

    endpoint = '/videos'

    @expose_ajax('/', cache_age=3600)
    def video_list(self):
        if not use_elasticsearch():
            data, total = get_local_videos(self.get_locale(), self.get_page(), star_order=True, **request.args)
            return dict(videos=dict(items=data, total=total))

        date_order = request.args.get('date_order')
        if app.config.get('DOLLY'):
            date_order = 'desc'
        category = request.args.get('category')
        if category:
            try:
                int(category)
            except ValueError:
                abort(400)

        vs = VideoSearch(self.get_locale())
        offset, limit = self.get_page()
        vs.set_paging(offset, limit)
        vs.filter_category(category)

        if app.config.get('DOLLY'):
            # Filter by tagged/added date
            vs.add_filter(filters.date_tagged_sort())
            vs.add_sort('_score', order='desc')

            # exclude favs
            f = pyes.TermFilter(field='is_favourite', value=False)
            vs._exclusion_filters.append(f)
        else:
            vs.star_order_sort(request.args.get('star_order'))
            vs.date_sort(date_order)

        location = self.get_location()
        if location:
            vs.check_country_allowed(location)

        videos = vs.videos(with_channels=True)
        total = vs.total

        return dict(videos={'items': videos}, total=total)

    @expose_ajax('/<video_id>/starring_users/', cache_age=3600)
    def video_starring_users(self, video_id):
        users = User.query.join(
            models.Channel,
            (models.Channel.owner == User.id) &
            (models.Channel.favourite == True)
        ).join(
            models.VideoInstance,
            (models.VideoInstance.channel == models.Channel.id) &
            (models.VideoInstance.video == video_id)
        ).order_by(
            models.VideoInstance.date_added.desc()
        )

        total = users.count()
        offset, limit = self.get_page()
        users = users.offset(offset).limit(limit)
        items = []
        for position, user in enumerate(users, offset):
            data = user_dict(user)
            data['position'] = position

        return dict(users={'items': items}, total=total)

    @expose_ajax('/<video_id>/channels/')
    def video_channels(self, video_id, cache_age=3600):
        vs = VideoSearch(self.get_locale())
        vs.add_term('video.id', video_id)
        vs.add_sort('child_instance_count')
        vs.set_paging(*self.get_page(default_size=5))
        videos = vs.videos(with_channels=True)
        if not videos:
            abort(404)
        return {'channels': {'items': [v['channel'] for v in videos], 'total': vs.total}}

    @expose_ajax('/players/', cache_age=7200)
    def players(self):
        return dict(models.Source.query.values(models.Source.label, models.Source.player_template))

    @expose_ajax('/player_error/', methods=['POST'])
    @check_authorization()
    def player_error(self):
        form = PlayerErrorForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)
        save_player_error(form.video_instance.data, form.error.data)

    @expose_ajax('/<video_instance_id>/activity/', methods=['POST'])
    @commit_on_success
    def anon_activity(self, video_instance_id):

        def add_instance(video_instance_id):
            instance = models.VideoInstanceAnonActivity(
                remote_address=request.remote_addr,
                object_id=video_instance_id)
            instance.add()
            return instance

        try:
            models.VideoInstanceAnonActivity.query.filter(
                models.VideoInstanceAnonActivity.remote_address == request.remote_addr,
                models.VideoInstanceAnonActivity.object_id == video_instance_id,
                models.VideoInstanceAnonActivity.date_added > (datetime.utcnow() - timedelta(hours=24))
            ).one()
        except NoResultFound:
            add_instance(video_instance_id)
        else:
            # Nothing to do here; dupe for the day.
            return

        from rockpack.mainsite.services.user.api import (increment_video_instance_counts,
                                                         _get_action_incrementer)

        video_id = models.VideoInstance.query.filter(
            models.VideoInstance.id == video_instance_id).value(models.VideoInstance.video)

        column, value, incr = _get_action_incrementer('view')
        increment_video_instance_counts(video_id, video_instance_id, 'en-us', incr, column)


class ChannelWS(WebService):

    endpoint = '/channels'

    @expose_ajax('/', cache_age=3600)
    def channel_list(self):
        def add_tracking(channel, extra=None):
            channel['tracking_code'] = ' '.join(filter(None, (
                'channel-browse',
                str(channel['position']),
                category and 'cat-%s' % category,
                extra)))
        category = request.args.get('category')
        get_channels = get_es_channels if use_elasticsearch() else get_db_channels
        items, total = get_channels(self.get_locale(), self.get_page(),
                                    category=category,
                                    add_tracking=add_tracking)
        return dict(channels=dict(items=items, total=total))


class CategoryWS(WebService):

    endpoint = '/categories'

    @expose_ajax('/', cache_age=3600)
    def category_list(self):
        translations = dict((c.category, (c.name, c.priority)) for c in
                            models.CategoryTranslation.query.filter_by(locale=self.get_locale()))
        items = []
        children = defaultdict(list)
        for cat in models.Category.query.all():
            name, priority = translations.get(cat.id, (None, None))
            if name:
                info = dict(id=str(cat.id), name=name, priority=priority)
                if cat.parent:
                    if cat.name == 'other':
                        info['default'] = True
                    children[cat.parent].append(info)
                else:
                    info['sub_categories'] = children[cat.id]
                    items.append(info)
                if cat.colour:
                    info['colour'] = cat.colour
        return dict(categories=dict(items=items))


class MoodWS(WebService):

    endpoint = '/moods'

    @expose_ajax('/', cache_age=3600)
    def mood_list(self):
        items = map(
            lambda m: dict(
                id=m.name,
                name=m.display_name
            ),
            models.Mood.query.all())
        return dict(moods=dict(items=items))


class OoyalaWS(WebService):

    endpoint = '/ooyala'

    @expose_ajax('/callback')
    @secure_view()
    @commit_on_success
    def callback(self):
        videoid = request.args['embedCode']
        if models.Video.query.filter_by(source_videoid=videoid).count():
            return
        try:
            data = ooyala.get_video_data(videoid, fetch_metadata=True)
        except Exception, e:
            if hasattr(e, 'response') and e.response.status_code == 404:
                abort(404)
            raise
        models.Video.add_videos(data.videos, models.Source.label_to_id('ooyala'))
        meta = data.videos[0].meta
        if 'channel' in meta:
            channel = models.Channel.query.get(meta['channel'])
            if not channel:
                app.logger.warning('Unable to add Ooyala video (%s) to channel: %s',
                                   videoid, meta['channel'])
                return
            try:
                category = models.Category.query.filter_by(
                    id=meta['category']).value('id')
            except Exception:
                category = None
            channel.add_videos(data.videos, category=category, tags=meta.get('tags'))
            app.logger.debug('Added ooyala video "%s" to "%s"', videoid, channel.id)
        # TODO: Notify somebody?
