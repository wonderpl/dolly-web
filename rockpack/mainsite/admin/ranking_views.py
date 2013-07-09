from flask.ext import login
from flask.ext.admin import BaseView, expose
from flask import request
from rockpack.mainsite import app
from rockpack.mainsite.admin.video_views import category_list
from rockpack.mainsite.core.es.api import ChannelSearch
from rockpack.mainsite.core.es import filters


class RankingView(BaseView):
    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()

    @expose('/', ('GET',))
    def index(self):
        category = int(request.args.get('category', 0))
        locale = request.args.get('locale', 'en-us')

        ctx = {'categories': category_list(),
                'image_cdn': app.config['IMAGE_CDN'],
                'category': category,
                'locale': locale}

        if category == 0:
            category = None

        print locale
        cs = ChannelSearch(locale)
        offset, limit = request.args.get('start', 0), request.args.get('size', 10)
        cs.set_paging(offset, limit)
        cs.add_filter(filters.boost_from_field_value('editorial_boost'))
        cs.add_filter(filters.boost_from_field_value('subscriber_frequency'))
        cs.add_filter(filters.boost_from_field_value('update_frequency', reduction_factor=4))
        cs.add_filter(filters.negatively_boost_favourites())
        cs.add_filter(filters.verified_channel_boost())
        cs.add_filter(filters.boost_by_time())
        cs.filter_category(category)
        cs.promotion_settings(category)
        cs.add_sort('promotion', 'desc')
        cs.add_sort('_score', 'desc')
        processed_channels = cs.channels(with_owners=True)

        ctx['channels'] = []

        # loop once to get the raw data
        raw_channels = {}
        for channel in cs.results():
            c = {}
            c['id'] = channel.id
            c['title'] = channel.title
            c['editorial_boost'] = channel.editorial_boost
            c['date_added'] = channel.date_added
            c['cover_thumbnail_large_url'] = channel.cover_thumbnail_large_url
            c['explanation'] = channel.__dict__['_meta']['explanation']
            c['subscriber_frequncy'] = channel.subscriber_frequncy
            c['subscriber_count'] = channel.subscriber_count
            c['video_update_frequency'] = channel.update_frequency
            c['subscriber_count'] = channel.subscriber_count
            c['promotion'] = channel.promotion
            c['gbcount'] = channel.locales['en-gb']['view_count']
            c['uscount'] = channel.locales['en-us']['view_count']
            raw_channels[channel.id] = c

        # loop again to get the correct order
        for channel in processed_channels:
            c = raw_channels[channel['id']]
            promo_string = '|'.join([locale, str(category or 0), str(channel['position'] + 1)])
            c['promoted'] = False
            print promo_string, c['promotion'], c['title']
            if promo_string in c['promotion']:
                c['promoted'] = True
            ctx['channels'].append(c)

        return self.render('admin/ranking.html', **ctx)
