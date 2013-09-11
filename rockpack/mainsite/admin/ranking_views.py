from flask.ext import login
from flask.ext.admin import BaseView, expose
from flask import request, redirect
from rockpack.mainsite import app
from rockpack.mainsite.admin.video_views import category_list
from rockpack.mainsite.core.es.api import ChannelSearch, VideoSearch
from rockpack.mainsite.core.es import filters


class RankingView(BaseView):
    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()

    @expose('/locale/<locale>/<channelid>/', ('GET',))
    def channel_videos(self, locale, channelid):
        offset, limit = request.args.get('start', 0), request.args.get('size', 20)
        order_by_position = request.args.get('position', 'f')

        vs = VideoSearch(locale)
        vs.add_term('channel', [channelid])
        if not order_by_position == 't':
            vs.add_sort('position', 'asc')
        vs.date_sort('desc')
        vs.add_sort('video.date_published', 'desc')
        vs.set_paging(offset, limit)

        ctx = {'videos': [],
            'image_cdn': app.config['IMAGE_CDN'],
            'referrer': request.args.get('referrer', request.referrer),
            'url': request.url,
            'path': request.path,
            'position': order_by_position}

        for video in vs.results():
            c = {}
            c['id'] = video.id
            c['title'] = video.title
            try:
                c['date_added'] = video.date_added[:10]
            except TypeError:
                c['date_added'] = video.date_added.isoformat()[:10]
            c['thumbnail_url'] = video.video.thumbnail_url
            c['explanation'] = video.__dict__['_meta']['explanation']
            c['duration'] = video.video.duration
            c['source'] = ['rockpack', 'youtube'][video.video.source]
            c['source_id'] = video.video.source_id
            c['subscriber_count'] = video.subscriber_count
            c['gbcount'] = video.locales['en-gb']['view_count']
            c['uscount'] = video.locales['en-us']['view_count']
            c['gbstarcount'] = video.locales['en-gb']['star_count']
            c['usstarcount'] = video.locales['en-us']['star_count']
            ctx['videos'].append(c)

        cs = ChannelSearch(locale)
        cs.add_id(channelid)
        channel = cs.channels()[0]
        ctx['channel'] = channel
        ctx['video_count'] = vs.total

        return self.render('admin/ranking.html', **ctx)

    @expose('/', ('GET',))
    def index(self):
        return redirect(request.url + 'locale/en-gb/')

    @expose('/locale/<string:locale>/', ('GET',))
    def ranking_locale(self, locale):
        category = int(request.args.get('category', 0))
        search = request.args.get('search')

        toggle_locale = {'en-us': 'en-gb', 'en-gb': 'en-us'}.get(locale)
        ctx = {
            'locale_base': self.url + '/locale/' + locale + '/',
            'locale_toggle_name': toggle_locale,
            'locale_toggle': self.url + '/locale/' + toggle_locale + '/',
            'categories': category_list(),
            'image_cdn': app.config['IMAGE_CDN'],
            'category': category,
            'locale': locale,
            'search_term': request.args.get('search', 'Search for a channel')}

        if category == 0:
            category = None

        cs = ChannelSearch(locale)
        offset, limit = request.args.get('start', 0), request.args.get('size', 20)
        cs.set_paging(offset, limit)
        if search:
            cs.add_text('title', search)
        else:
            cs.add_filter(filters.boost_from_field_value('editorial_boost'))
            cs.add_filter(filters.channel_rank_boost(locale))
            cs.add_filter(filters.negatively_boost_favourites())
            cs.filter_category(category)
            cs.promotion_settings(category)
        processed_channels = cs.channels(with_owners=True)

        ctx['channels'] = []

        # loop once to get the raw data
        raw_channels = {}
        for channel in cs.results():
            c = {}
            c['id'] = channel.id
            c['title'] = channel.title
            c['editorial_boost'] = channel.editorial_boost
            try:
                c['date_added'] = channel.date_added[:10]
            except TypeError:
                c['date_added'] = channel.date_added.isoformat()[:10]
            c['cover_thumbnail_large_url'] = channel.cover_thumbnail_large_url
            c['explanation'] = channel.__dict__['_meta']['explanation']
            c['subscriber_frequency'] = channel.subscriber_frequency
            c['subscriber_count'] = channel.subscriber_count
            c['video_update_frequency'] = channel.update_frequency
            c['subscriber_count'] = channel.subscriber_count
            c['promotion'] = channel.promotion
            c['gbcount'] = channel.locales['en-gb']['view_count']
            c['uscount'] = channel.locales['en-us']['view_count']
            c['normalised_rank'] = channel.normalised_rank
            raw_channels[channel.id] = c

        # loop again to get the correct order
        for channel in processed_channels:
            c = raw_channels[channel['id']]
            promo_string = '|'.join([locale, str(category or 0), str(channel['position'] + 1)])
            c['promoted'] = False
            if c.get('promotion', []) and promo_string in c.get('promotion', []):
                c['promoted'] = True
            ctx['channels'].append(c)

        return self.render('admin/ranking.html', **ctx)
