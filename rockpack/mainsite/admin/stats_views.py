from datetime import datetime, date, time, timedelta
from sqlalchemy import func, between, literal, text, Integer
from sqlalchemy.orm import aliased
from flask import request
from flask.ext.admin import expose
from rockpack.mainsite import app
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.core.dbapi import readonly_session
from rockpack.mainsite.core.es import search
from .base import AdminView


LAUNCHDATE = '2014-03-13' if app.config.get('DOLLY') else '2013-06-26'


class StatsView(AdminView):

    def __init__(self, *args, **kwargs):
        name = self.__class__.__name__
        if name.endswith('StatsView'):
            name = name[:-9]
        kwargs.setdefault('name', name)
        kwargs.setdefault('endpoint', 'stats/%s' % name.lower())
        super(StatsView, self).__init__(*args, **kwargs)


class UserCategoriesStatsView(StatsView):
    @expose('/')
    def index(self):
        from rockpack.mainsite.services.video.models import Category
        ctx = {}

        parent = aliased(Category)
        cat_group = readonly_session.query(
            Category.name,  # order is important
            parent.name,
            Category.id
        ).filter(
            Category.parent == parent.id
        ).group_by(
            parent.name,
            Category.name,
            Category.id
        ).order_by(parent.name, Category.name)

        cat_map = []

        for (child_name, parent_name, child_id) in cat_group:
            users = search.UserSearch()
            users.add_term('category', child_id)
            users.set_paging(1, 0)
            users.users()
            cat_map.append(
                (parent_name,
                 child_name,
                 users.total,
                 '/admin/stats/usercategories/%s/' % child_id))

        ctx['cat_map'] = cat_map

        return self.render('admin/user_cat_stats.html', **ctx)

    @expose('/<cat_id>/')
    def users(self, cat_id):
        ctx = {}

        page_size = 50
        users = search.UserSearch()
        users.add_term('category', cat_id)
        users.set_paging(int(request.args.get('p', 0)) * page_size, page_size - 1)
        result = users.users()

        from rockpack.mainsite.services.video.models import Category

        parent = aliased(Category)
        query = readonly_session.query(
            Category.name,  # order is important
            parent.name,
            Category.id
        ).filter(
            Category.parent == parent.id,
            Category.id == cat_id
        )

        ctx['next_page'] = int(request.args.get('p', 1)) + 1
        ctx['category'] = query.one()
        ctx['single_cat'] = True
        ctx['users'] = result
        return self.render('admin/user_cat_stats.html', **ctx)


class ContentStatsView(StatsView):
    @expose('/')
    def index(self):
        from rockpack.mainsite.services.video import models
        channels = readonly_session.query(models.Channel)

        public = channels.join(models.ChannelLocaleMeta).filter(
            models.ChannelLocaleMeta.visible == True, models.Channel.public == True)

        parent = aliased(models.Category)

        cat_group = readonly_session.query(
            models.Category.name,   # order is important
            parent.name,
            func.count(models.VideoInstance.id)
        ).outerjoin(models.VideoInstance).filter(
            models.Category.parent == parent.id
        ).group_by(
            parent.name,
            models.Category.name
        ).order_by(parent.name, models.Category.name)

        cat_count = cat_group.count()

        kwargs = dict(now=datetime.now().strftime('%Y-%m-%d'),
                      cat_group=cat_group.all(),
                      cat_count=cat_count,
                      is_dolly=app.config.get('DOLLY'))

        if not app.config.get('DOLLY'):
            channel_group = readonly_session.query(
                models.ChannelLocaleMeta.locale,
                parent.name,
                models.Category.name,
                func.count(models.ChannelLocaleMeta.id)
            ).filter(
                models.Category.parent == parent.id,
                models.Channel.category == models.Category.id
            ).filter(
                models.Category.parent != 1
            ).join(
                models.Channel, models.Channel.id == models.ChannelLocaleMeta.channel
            ).filter(
                models.Channel.public == True
            ).group_by(
                models.Category.parent_category,
                models.Category.name,
                parent.name,
                models.ChannelLocaleMeta.locale
            ).order_by(parent.name.desc())
            channel_count = channel_group.count()

            channels_today = channels.filter(
                models.Channel.date_added >= datetime.now().strftime('%Y-%m-%d')).count()

            kwargs.update(dict(
                total_channels=channels.count(),
                total_channels_today=channels_today,
                public_channels=public.count(),
                channels_today=channels_today,
                channel_group=channel_group.all(),
                channel_count=channel_count))

        return self.render(
            'admin/stats.html',
            **kwargs
        )


class AppStatsView(StatsView):
    @expose('/')
    def index(self):
        from gviz_data_table import Table
        from rockpack.mainsite.services.user.models import User
        from .models import AppDownloadRecord
        ctx = {}
        for action in 'download', 'update':
            table = Table((dict(id='date', type=date), dict(id='count', type=long)))
            table.extend(
                readonly_session.query(AppDownloadRecord).filter_by(action=action).
                group_by('1').order_by('1').
                values(AppDownloadRecord.date, func.sum(AppDownloadRecord.count))
            )
            ctx['%s_data' % action] = table.encode()
        table = Table([dict(id='date', type=date)] +
                      [dict(id=i, type=long) for i in 'Total', 'US', 'UK', 'Other'])
        table.extend(
            readonly_session.query(User).filter(
                User.date_joined > LAUNCHDATE, User.refresh_token != None).
            group_by('1').order_by('1').
            values(
                func.date(User.date_joined),
                func.count('*'),
                func.sum(func.cast(User.locale == 'en-us', Integer)),
                func.sum(func.cast(User.locale == 'en-gb', Integer)),
                func.sum(func.cast(User.locale.notin_(('en-us', 'en-gb')), Integer)),
            )
        )
        ctx['reg_data'] = table.encode()
        return self.render('admin/app_stats.html', **ctx)


class ActivityStatsView(StatsView):
    @expose('/')
    def index(self):
        from gviz_data_table import Table
        from rockpack.mainsite.services.user.models import UserActivity
        table = Table([dict(id='date', type=date)] +
                      [dict(id=i, type=long) for i in
                       'Total', 'Unique Users', 'Views', 'Subscriptions', 'Plusses', 'Likes'])
        table.extend(
            readonly_session.query(UserActivity).filter(UserActivity.date_actioned > LAUNCHDATE).
            group_by('1').order_by('1').
            values(
                func.date(UserActivity.date_actioned),
                func.count('*'),
                func.count(func.distinct(UserActivity.user)),
                func.sum(func.cast(UserActivity.action == 'view', Integer)),
                func.sum(func.cast(UserActivity.action == 'subscribe', Integer)),
                func.sum(func.cast(UserActivity.action == 'select', Integer)),
                func.sum(func.cast(UserActivity.action == 'star', Integer))
            )
        )
        return self.render('admin/activity_stats.html', activity_data=table.encode())


class RetentionStatsView(StatsView):
    @expose('/')
    def index(self):
        from gviz_data_table import Table
        from rockpack.mainsite.services.user.models import User, UserActivity, UserAccountEvent
        if request.args.get('activity') == 'activity':
            activity_model, activity_date = UserActivity, UserActivity.date_actioned
        else:
            activity_model, activity_date = UserAccountEvent, UserAccountEvent.event_date

        cohort = func.date_part('week', User.date_joined)
        cohort_label = func.max(func.date(User.date_joined))
        weeks_active = (func.date_part('week', activity_date) - cohort).label('weeks_active')

        q = readonly_session.query(User).filter(
            User.date_joined > LAUNCHDATE, User.refresh_token != '')
        if request.args.get('gender') in ('m', 'f'):
            q = q.filter(User.gender == request.args['gender'])
        if request.args.get('locale') in app.config['ENABLED_LOCALES']:
            q = q.filter(User.locale == request.args['locale'])
        if request.args.get('age') in ('13-18', '18-25', '25-35', '35-45', '45-55'):
            age1, age2 = map(int, request.args['age'].split('-'))
            q = q.filter(between(
                func.age(User.date_of_birth),
                text("interval '%d years'" % age1),
                text("interval '%d years'" % age2)
            ))

        totals = dict(q.group_by(cohort).values(cohort_label, func.count('*')))
        active_users = dict(
            ((c, int(w)), u) for c, w, u in
            q.join(
                activity_model,
                (activity_model.user == User.id) &
                (activity_date > User.date_joined)
            ).group_by(cohort, weeks_active).values(
                cohort_label, weeks_active, func.count(func.distinct(activity_model.user))
            )
        )

        table = Table(
            [dict(id='cohort', type=date)] +
            [dict(id='week%d' % i, type=str) for i in range(10)]
        )

        for c, t in sorted(totals.items()):
            data = []
            for i in range(10):
                a = active_users.get((c, i), '')
                data.append(a and '%s%% (%s)' % (a * 100 / t, a))
            table.append([c] + data)

        return self.render('admin/retention_stats.html', data=table.encode())

    @expose('/old/')
    def index_old(self):
        from gviz_data_table import Table
        from rockpack.mainsite.services.user.models import User, UserActivity
        user_count = readonly_session.query(func.count(User.id)).\
            filter(User.refresh_token != '').scalar()
        header = ('user count', 'max lifetime', 'avg lifetime', 'stddev lifetime',
                  'max active days', 'avg active days', 'stddev active days')
        lifetime = func.date_part('days', func.max(UserActivity.date_actioned) -
                                  func.min(UserActivity.date_actioned)).label('lifetime')
        active_days = func.count(func.distinct(func.date(
            UserActivity.date_actioned))).label('active_days')
        activity = readonly_session.query(UserActivity.user, lifetime, active_days).\
            group_by(UserActivity.user)
        ctx = {}
        for key, having_expr in ('all', None), ('1day', lifetime > 1), ('7day', lifetime > 7):
            data = activity.having(having_expr).from_self(
                func.count('*'),
                func.max(lifetime),
                func.avg(lifetime),
                func.stddev_samp(lifetime),
                func.max(active_days),
                func.avg(active_days),
                func.stddev_samp(active_days)
            ).one()
            table = Table([
                dict(id='metric', type=str),
                dict(id='value', type=float),
                dict(id='%', type=str),
            ])
            pdata = ('%d%%' % (data[0] * 100 / user_count),) + ('',) * 6
            table.extend(zip(*(header, map(float, data), pdata)))
            ctx['ret_%s_data' % key] = table.encode()

        return self.render('admin/retention_stats_old.html', **ctx)


class TableStatsView(StatsView):

    periods = ('day', 1), ('week', 7), ('month', 31)
    counts = 'view', 'star', 'share'
    sortindex_base = 1
    item_label = 'item'

    def get_table_head(self):
        return ([dict(id=self.item_label, type=str)] +
                [dict(id='%s count' % c, type=int) for c in self.counts])

    def _item_link(self, endpoint, id, label, param='id'):
        return ('<a href="%s?%s=%s">%s</a>' % (url_for(endpoint), param, id, label)).encode('utf8')

    def user_item(self, id, username):
        return self._item_link('user.edit_view', id, username)

    def channel_item(self, id, title):
        return self._item_link('video_instance.index_view', id, title, 'flt0_0')

    def video_item(self, id, title):
        return self._item_link('video_instance.index_view', id, title, 'flt1_4')

    @expose('/')
    def index(self):
        from gviz_data_table import Table

        try:
            period = dict(self.periods)[request.args.get('period')]
        except:
            period = self.periods[0][1]

        dates = {'from': datetime.combine(date.today() - timedelta(days=period), time.min)}
        dates['to'] = dates['from'] + timedelta(days=period)
        for param in 'from', 'to':
            try:
                dates[param] = datetime.strptime(request.args[param], '%Y-%m-%d %H:%M')
            except:
                pass

        try:
            sortindex = self.counts.index(request.args.get('sort')) + self.sortindex_base
        except:
            sortindex = self.sortindex_base

        try:
            limit = int(request.args['limit'])
        except:
            limit = 20

        table = Table(self.get_table_head())
        for row in self.get_query(dates['from'], dates['to']).\
                order_by('%d desc' % sortindex).limit(limit):
            item, counts = self.split_row(row)
            table.append(item + [int(i) if i else 0 for i in counts])

        selects = ('sort', self.counts), ('period', zip(*self.periods)[0])
        return self.render('admin/chart_table.html',
                           data=table.encode(),
                           selects=selects,
                           dates=sorted(dates.items()))


class TopUsersStatsView(TableStatsView):

    counts = 'activity', 'view', 'star', 'subscribe', 'share', 'click'
    sortindex_base = 3
    item_label = 'user'

    def get_query(self, date_from, date_to):
        from rockpack.mainsite.services.video.models import Channel, VideoInstance
        from rockpack.mainsite.services.user.models import User, UserActivity
        from rockpack.mainsite.services.share.models import ShareLink

        activity = readonly_session.query(
            func.coalesce(VideoInstance.channel, UserActivity.object_id).label('channel'),
            UserActivity.action.label('action'),
            literal(0).label('click_count')
        ).select_from(
            UserActivity
        ).outerjoin(
            VideoInstance, VideoInstance.id == UserActivity.object_id
        ).filter(
            UserActivity.date_actioned.between(date_from, date_to)
        )
        shares = readonly_session.query(
            func.coalesce(VideoInstance.channel, ShareLink.object_id).label('channel'),
            literal('share').label('action'),
            ShareLink.click_count.label('click_count')
        ).select_from(
            ShareLink
        ).outerjoin(
            VideoInstance, VideoInstance.id == ShareLink.object_id
        ).filter(
            ShareLink.date_created.between(date_from, date_to)
        )
        activity = activity.union_all(shares).subquery()

        query = readonly_session.query(
            *self._cols(Channel, User, activity)
        ).select_from(
            Channel
        ).join(
            activity, activity.c.channel == Channel.id
        ).join(
            User, User.id == Channel.owner
        )

        return self._agg_query(query, Channel, User, activity)

    def split_row(self, row):
        return [self.user_item(*row[:2])], row[2:]

    def _cols(self, Channel, User, activity):
        return ([User.id, User.username, func.count()] +
                [func.sum(func.cast(activity.c.action == c, Integer)) for c in self.counts[1:-1]] +
                [func.sum(activity.c.click_count)])

    def _agg_query(self, query, Channel, User, activity):
        return query.group_by(User.id)


class TopChannelsStatsView(TopUsersStatsView):

    item_label = 'channel'
    sortindex_base = 5

    def get_table_head(self):
        cols = super(TopChannelsStatsView, self).get_table_head()
        return cols[:1] + [dict(id='owner', type=str)] + cols[1:]

    def split_row(self, row):
        cid, ctitle, uid, username = row[:4]
        return [self.channel_item(cid, ctitle), self.user_item(uid, username)], row[4:]

    def _cols(self, Channel, User, activity):
        cols = super(TopChannelsStatsView, self)._cols(Channel, User, activity)
        return [Channel.id, Channel.title] + cols

    def _agg_query(self, query, Channel, User, activity):
        return query.filter(Channel.favourite == False).group_by(Channel.id, User.id)


class TopVideosStatsView(TableStatsView):

    counts = 'activity', 'instance', 'view', 'star', 'share', 'click'
    sortindex_base = 3
    item_label = 'video'

    def get_query(self, date_from, date_to):
        from rockpack.mainsite.services.video.models import Video, VideoInstance
        from rockpack.mainsite.services.user.models import UserActivity
        from rockpack.mainsite.services.share.models import ShareLink

        activity = readonly_session.query(
            UserActivity.object_id.label('video_instance'),
            UserActivity.action.label('action'),
            literal(0).label('click_count')
        ).filter(
            UserActivity.object_type == 'video_instance',
            UserActivity.date_actioned.between(date_from, date_to)
        )
        shares = readonly_session.query(
            ShareLink.object_id.label('video_instance'),
            literal('share').label('action'),
            ShareLink.click_count.label('click_count')
        ).filter(
            ShareLink.object_type == 'video_instance',
            ShareLink.date_created.between(date_from, date_to)
        )
        activity = activity.union_all(shares).subquery()

        query = readonly_session.query(
            Video.id,
            Video.title,
            func.count(activity.c.video_instance),
            func.count(VideoInstance.id.distinct()),
            *([func.sum(func.cast(activity.c.action == c, Integer)) for c in self.counts[2:-1]] +
              [func.sum(activity.c.click_count)])
        ).join(
            VideoInstance, VideoInstance.video == Video.id
        ).join(
            activity, activity.c.video_instance == VideoInstance.id
        ).group_by(
            Video.id
        )

        return query

    def split_row(self, row):
        return [self.video_item(*row[:2])], row[2:]


class SlicerStatsView(StatsView):

    @expose('/')
    def index(self):
        ctx = {}
        return self.render('admin/slicer_stats.html', **ctx)
