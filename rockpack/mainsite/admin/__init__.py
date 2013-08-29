from flask.ext.admin import Admin
from . import video_views, import_views, user_views, ranking_views, stats_views


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
    admin.add_view(user_views.BroadcastMessageView(name='Broadcast Messages', endpoint='broadcast', category='Users'))
    admin.add_view(import_views.ImportView(name='Import', endpoint='import'))
    admin.add_view(ranking_views.RankingView(name='Ranking', endpoint='ranking'))
    admin.add_view(stats_views.ContentStatsView(name='Content', endpoint='stats/content', category='Stats'))
    admin.add_view(stats_views.AppStatsView(name='Downloads', endpoint='stats/downloads', category='Stats'))
    admin.add_view(stats_views.ActivityStatsView(name='User Activity', endpoint='stats/activity', category='Stats'))
    admin.add_view(stats_views.RetentionStatsView(name='Retention', endpoint='stats/retention', category='Stats'))

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
