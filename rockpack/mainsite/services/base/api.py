from flask import request, g
from rockpack.mainsite import app
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.core.oauth.decorators import check_authorization


def _discover_response():
    locale = request.args.get('locale', app.config['ENABLED_LOCALES'][0])
    return dict(
        categories=url_for('categoryws.category_list', locale=locale),
        popular_channels=url_for('channelws.channel_list', locale=locale),
        popular_videos=url_for('videows.video_list', locale=locale),
        channel_search=url_for('searchws.search_channels', locale=locale),
        channel_search_terms=url_for('completews.complete_channel_terms', locale=locale),
        video_search=url_for('searchws.search_videos', locale=locale),
        video_search_terms=url_for('completews.complete_video_terms', locale=locale),
        cover_art=url_for('coverartws.rockpack_cover_art', locale=locale),
        login=url_for('loginws.login'),
        register=url_for('registrationws.register'),
        login_register_external=url_for('loginws.exeternal'),
        reset_password=url_for('resetws.reset_password'),
        refresh_token= url_for('tokenws.token'),
    )


class BaseWS(WebService):

    endpoint = '/'

    @expose_ajax('/', cache_age=60, secure=False)
    def discover(self):
        return _discover_response()

    @expose_ajax('/', cache_age=60, cache_private=True, secure=True)
    @check_authorization()
    def secure_discover(self):
        result = _discover_response()
        if g.authorized:
            result.update(dict(
                user=url_for('userws.own_user_info', userid=g.authorized.userid),
                subscription_updates=url_for('userws.recent_videos', userid=g.authorized.userid),
            ))
        return result
