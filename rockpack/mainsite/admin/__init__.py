from flask.ext.admin import Admin, BaseView
from . import video_views, import_views, user_views, ranking_views, stats_views
from .base import AdminView, AdminModelView


def setup_admin(app):
    # init commands:
    from . import commands
    commands    # for pyflakes

    subdomain = app.config.get('ADMIN_SUBDOMAIN')
    admin_name = app.config.get('ADMIN_NAME', 'Rockpack Admin')
    admin = Admin(app, endpoint='admin', subdomain=subdomain, name=admin_name)

    for module, category in (video_views, 'Content'), (user_views, 'Users'), (stats_views, 'Stats'):
        map(admin.add_view, sorted(
            [
                view(category=category)
                for view in module.__dict__.itervalues()
                if (isinstance(view, type) and issubclass(view, BaseView) and
                    # exclude base classes:
                    view not in (AdminView, AdminModelView, stats_views.StatsView, stats_views.TableStatsView) and
                    not getattr(view, 'inline_model', False))
            ], key=lambda v: v.name))

    admin.add_view(import_views.ImportView(name='Import', endpoint='import', category='Import'))
    admin.add_view(import_views.UploadView(name='Review Uploads', endpoint='review', category='Import'))
    if app.config.get('DOLLY'):
        admin.add_view(ranking_views.UserRankingView(name='Ranking', endpoint='ranking'))
    else:
        admin.add_view(ranking_views.RankingView(name='Ranking', endpoint='ranking'))

    # Need to import here to avoid import uninitialised google_oauth decorator
    from .auth.views import login, logout, oauth_callback
    for view in login, logout, oauth_callback:
        app.add_url_rule('%s/%s' % (admin.url, view.func_name), view.func_name, view, subdomain=subdomain)

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

    from cubes.server import slicer
    app.register_blueprint(slicer, url_prefix='/admin/slicer', config='slicer.ini')
