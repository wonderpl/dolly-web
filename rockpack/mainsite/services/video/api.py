import wtforms as wtf
from flask import request, abort
from flask.ext.wtf import Form
from collections import defaultdict
from sqlalchemy.orm import contains_eager, lazyload, joinedload
from sqlalchemy.sql.expression import desc
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import readonly_session, db, commit_on_success
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.core.es import use_elasticsearch, filters
from rockpack.mainsite.core.es.search import VideoSearch, ChannelSearch, UserSearch
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.user.models import UserActivity


def _filter_by_category(query, type, category_id):
    """Filter given query by the specified category.
    If top-level category given, then filter by all sub categories.
    """
    sub_cats = list(models.Category.query.filter_by(parent=category_id).
                    values(models.Category.id))
    cat_ids = zip(*sub_cats)[0] if sub_cats else [category_id]
    return query.filter(type.category.in_(cat_ids))


def channel_dict(channel, position=None, with_owner=True, owner_url=False, add_tracking=None):
    ch_data = dict(
        id=channel.id,
        resource_url=channel.get_resource_url(owner_url),
        title=channel.title,
        subscriber_count=channel.subscriber_count,
        category=channel.category,
        date_published=channel.date_published and channel.date_published.isoformat(),
        cover=dict(
            thumbnail_url=channel.cover.url,
            aoi=channel.cover_aoi,
        )
    )
    if channel.favourite:
        ch_data['favourites'] = True
    if channel.verified:
        ch_data['verified'] = True
    if with_owner:
        ch_data['owner'] = dict(
            id=channel.owner_rel.id,
            resource_url=channel.owner_rel.get_resource_url(owner_url),
            display_name=channel.owner_rel.display_name,
            avatar_thumbnail_url=channel.owner_rel.avatar.thumbnail_medium,
        )
    if owner_url:
        ch_data['public'] = channel.public
    if position is not None:
        ch_data['position'] = position
    if app.config.get('SHOW_CHANNEL_DESCRIPTION', False):
        ch_data['description'] = channel.description
    if app.config.get('SHOW_OLD_CHANNEL_COVER_URLS', True):
        for k in 'thumbnail_large', 'thumbnail_small', 'background':
            ch_data['cover_%s_url' % k] = getattr(channel.cover, k)
    if add_tracking:
        add_tracking(ch_data)
    return ch_data


def get_db_channels(locale, paging, add_tracking=None, **filters):
    channels = models.Channel.query.filter_by(public=True, deleted=False).\
        outerjoin(
            models.ChannelLocaleMeta,
            ((models.ChannelLocaleMeta.channel == models.Channel.id) &
            (models.ChannelLocaleMeta.locale == locale))).\
        options(lazyload('category_rel'))

    if filters.get('channels'):
        channels = channels.filter(models.Channel.id.in_(filters['channels']))
    if filters.get('category'):
        channels = _filter_by_category(channels, models.Channel, filters['category'])
    if filters.get('query'):
        channels = channels.filter(models.Channel.title.ilike('%%%s%%' % filters['query']))

    if filters.get('date_order'):
        channels = channels.order_by(desc(models.Channel.date_added))

    total = channels.count()
    offset, limit = paging
    channels = channels.offset(offset).limit(limit)
    items = [channel_dict(channel, position, add_tracking=add_tracking)
             for position, channel in enumerate(channels, offset)]

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
    return dict(
        id=instance.id,
        title=video.title,
        date_added=instance.date_added.isoformat(),
        video=dict(
            id=video.id,
            source=['rockpack', 'youtube'][video.source],    # TODO: read source map from db
            source_id=video.source_videoid,
            source_username=video.source_username,
            duration=video.duration,
            view_count=video.view_count,
            star_count=video.star_count,
            thumbnail_url=video.default_thumbnail,
        )
    )


def get_local_videos(loc, paging, with_channel=True, include_invisible=False, readonly_db=False, **filters):
    if readonly_db:
        videos = readonly_session.query(models.VideoInstance)
    else:
        videos = db.session.query(models.VideoInstance)

    videos = videos.join(
        models.Video, models.Video.id == models.VideoInstance.video).\
        options(contains_eager(models.VideoInstance.video_rel))
    if include_invisible is False:
        videos = videos.filter(models.Video.visible == True)
    if with_channel:
        videos = videos.options(joinedload(models.VideoInstance.video_channel))

    if filters.get('channel'):
        filters.setdefault('channels', [filters['channel']])

    if filters.get('channels'):
        videos = videos.filter(models.VideoInstance.channel.in_(filters['channels']))

    if filters.get('category'):
        videos = _filter_by_category(videos, models.VideoInstance, filters['category'][0])

    if filters.get('position_order'):
        videos = videos.order_by(models.VideoInstance.position)

    if filters.get('star_order'):
        videos = videos.outerjoin(
            models.VideoInstanceLocaleMeta,
            (models.VideoInstanceLocaleMeta.video_instance == models.VideoInstance.id) &
            (models.VideoInstanceLocaleMeta.locale == loc))
        videos = videos.order_by(desc(models.VideoInstanceLocaleMeta.star_count))

    if filters.get('date_order'):
        videos = videos.order_by(desc(models.VideoInstance.date_added)).\
            order_by(desc(models.Video.date_published))

    total = videos.count()
    offset, limit = paging
    videos = videos.offset(offset).limit(limit)
    data = []
    for position, video in enumerate(videos, offset):
        item = video_dict(video)
        item['position'] = position
        if with_channel:
            item['channel'] = channel_dict(video.video_channel)
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

        location = request.args.get('location')
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
        vs.star_order_sort(request.args.get('star_order'))
        vs.date_sort(date_order)
        if location:
            vs.check_country_allowed(location.upper())
        videos = vs.videos(with_channels=True)
        total = vs.total

        return dict(videos={'items': videos}, total=total)

    @expose_ajax('/<video_id>/starring_users/', cache_age=3600)
    def video_starring_users(self, video_id):
        query = readonly_session.query(UserActivity.user).join(
            models.VideoInstance,
            models.VideoInstance.id == UserActivity.object_id
        ).filter(
            UserActivity.object_type == 'video_instance',
            UserActivity.action == 'star',
            models.VideoInstance.video == video_id
        )
        user_ids = [_ for _ in query]
        if not user_ids:
            abort(404)

        u = UserSearch()
        u.add_id(user_ids)
        u.set_paging(*self.get_page())
        users = u.users()

        if not users:
            abort(404)
        return dict(users=dict(items=users, total=len(users)))

    @expose_ajax('/<video_id>/channels/')
    def video_channels(self, video_id, cache_age=3600):
        v = VideoSearch(self.get_locale())
        v.add_term('video.id', video_id)
        v.set_paging(0, 5)
        videos = v.videos()
        if not videos:
            abort(404)
        return [v['channel_title'] for v in videos]

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


class ChannelWS(WebService):

    endpoint = '/channels'

    @expose_ajax('/', cache_age=3600)
    def channel_list(self):
        def add_tracking(channel, extra=None):
            channel['tracking_code'] = ' '.join(filter(None, (
                'browse',
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
        return dict(categories=dict(items=items))
