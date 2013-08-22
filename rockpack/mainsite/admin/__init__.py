from datetime import datetime, date
from flask import g
from flask.ext.admin import Admin, BaseView, expose
from sqlalchemy import func, Integer
from sqlalchemy.orm import aliased
from . import video_views, import_views, user_views, ranking_views


class ContentStats(BaseView):
    @expose('/')
    def index(self):
        from rockpack.mainsite.services.video import models
        channels = models.Channel.query
        public = channels.join(models.ChannelLocaleMeta).filter(
            models.ChannelLocaleMeta.visible == True, models.Channel.public == True)
        parent = aliased(models.Category)
        cat_group = g.session.query(
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

        channel_group = g.session.query(
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


class AppStats(BaseView):
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


def setup_admin(app):
    # init commands:
    from . import commands

    subdomain = app.config.get('ADMIN_SUBDOMAIN')
    admin = Admin(app, endpoint='admin', subdomain=subdomain, name='Rockpack Admin')

    # video
    for v in video_views.admin_views():
        admin.add_view(v)

    admin.add_view(user_views.UserView(name='Users', endpoint='user', category='Users'))
    admin.add_view(user_views.ExternalTokenView(name='External Accounts', endpoint='external_accounts', category='Users'))
    admin.add_view(import_views.ImportView(name='Import', endpoint='import'))
    admin.add_view(ranking_views.RankingView(name='Ranking', endpoint='ranking'))
    admin.add_view(ContentStats(name='Content', endpoint='stats/content', category='Stats'))
    admin.add_view(AppStats(name='Downloads', endpoint='stats/downloads', category='Stats'))

    # Need to import here to avoid import uninitialised google_oauth decorator
    from .auth.views import login, logout, oauth_callback
    for view in login, logout, oauth_callback:
        app.add_url_rule('%s/%s' % (admin.url, view.func_name), view.func_name, view, subdomain=subdomain)

    """ TODO: add these back in later
    admin.add_view(views.AdminView(
        name='Admin Users',
        endpoint='admin-user'))
    admin.add_view(views.RoleView(
        name='Roles',
        endpoint='permissions/roles',
        category='Permissions'))
    admin.add_view(views.PermissionView(
        name='Permissions',
        endpoint='permissions/permissions',
        category='Permissions'))
    admin.add_view(views.RolePermissionView(
        name='RolePermissions',
        endpoint='permissions/role-permissions',
        category='Permissions'))
    admin.add_view(views.AdminRoleView(
        name='AdminRoles',
        endpoint='permissions/admin-permissions',
        category='Permissions'))
    """

    original_edit_master = (admin.index_view.blueprint.jinja_loader.load(
        app.jinja_env, 'admin/model/edit.html'))

    original_create_master = (admin.index_view.blueprint.jinja_loader.load(
        app.jinja_env, 'admin/model/create.html'))

    @app.context_processor
    def original_edit_master_template():
        return {'original_edit_master': original_edit_master}

    @app.context_processor
    def original_create_master_template():
        return {'original_create_master': original_create_master}
