from datetime import datetime, date
from sqlalchemy import func, Integer
from sqlalchemy.orm import aliased
from flask.ext.admin import BaseView, expose


class ContentStatsView(BaseView):
    @expose('/')
    def index(self):
        from rockpack.mainsite.services.video import models
        channels = models.Channel.query
        session = channels.session

        public = channels.join(models.ChannelLocaleMeta).filter(
            models.ChannelLocaleMeta.visible == True, models.Channel.public == True)
        parent = aliased(models.Category)
        cat_group = session.query(
            models.VideoInstanceLocaleMeta.locale,
            parent.name,
            models.Category.name,
            func.count(models.VideoInstanceLocaleMeta.id)
        ).join(models.VideoInstance, models.Video).filter(
            models.Category.parent == parent.id,
            models.VideoInstance.category == models.Category.id
        ).filter(
            models.Category.parent != 1,
            models.Video.visible == True
        ).filter_by(
        ).group_by(
            models.Category.parent_category,
            models.Category.name,
            parent.name,
            models.VideoInstanceLocaleMeta.locale
        ).order_by(parent.name.desc())
        cat_count = cat_group.count()

        channel_group = session.query(
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

        return self.render(
            'admin/stats.html',
            now=datetime.now().strftime('%Y-%m-%d'),
            total_channels=channels.count(),
            total_channels_today=channels_today,
            public_channels=public.count(),
            cat_group=cat_group.all(),
            cat_count=cat_count,
            channel_group=channel_group.all(),
            channel_count=channel_count,
        )


class AppStatsView(BaseView):
    @expose('/')
    def index(self):
        from gviz_data_table import Table
        from rockpack.mainsite.services.user.models import User
        from .models import AppDownloadRecord
        ctx = {}
        for action in 'download', 'update':
            table = Table((dict(id='date', type=date), dict(id='count', type=long)))
            table.extend(
                AppDownloadRecord.query.filter_by(action=action).
                group_by('1').order_by('1').
                values(AppDownloadRecord.date, func.sum(AppDownloadRecord.count))
            )
            ctx['%s_data' % action] = table.encode()
        table = Table([dict(id='date', type=date)] +
                      [dict(id=i, type=long) for i in 'Total', 'US', 'UK', 'Other'])
        table.extend(
            User.query.filter(User.date_joined > '2013-06-26', User.refresh_token != None).
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


class ActivityStatsView(BaseView):
    @expose('/')
    def index(self):
        from gviz_data_table import Table
        from rockpack.mainsite.services.user.models import UserActivity
        table = Table([dict(id='date', type=date)] +
                      [dict(id=i, type=long) for i in
                       'Total', 'Unique Users', 'Views', 'Subscriptions', 'Plusses', 'Likes'])
        table.extend(
            UserActivity.query.filter(UserActivity.date_actioned > '2013-06-26').
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
