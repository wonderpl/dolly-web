from flask import request, g, json
from rockpack.mainsite import app
from rockpack.mainsite.helpers import get_country_code_from_address
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.core.webservice import WebService, expose_ajax, ajax_create_response
from rockpack.mainsite.core.oauth.decorators import check_authorization
from .models import SessionRecord


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
        login_register_external=url_for('loginws.external'),
        reset_password=url_for('resetws.reset_password'),
        refresh_token=url_for('tokenws.token'),
        share_url=url_for('sharews.create_share_link'),
        user_search=url_for('searchws.search_users'),
        base_api=url_for('basews.discover'),
    )


class BaseWS(WebService):

    endpoint = '/'

    @expose_ajax('/', cache_age=3600, secure=False)
    def discover(self):
        return _discover_response()

    @expose_ajax('/', cache_age=3600, cache_private=True, secure=True)
    @check_authorization(abort_on_fail=False)
    def secure_discover(self):
        result = _discover_response()
        if g.authorized:
            result.update(dict(
                user=url_for('userws.own_user_info', userid=g.authorized.userid),
                subscription_updates=url_for('userws.recent_videos', userid=g.authorized.userid),
            ))
        return result

    @expose_ajax('/location/', secure=True)
    def get_location(self):
        return get_country_code_from_address(request.remote_addr) or ''

    @expose_ajax('/session/', methods=['POST'], secure=True)
    @check_authorization(abort_on_fail=False)
    def post_session(self):
        value = request.json
        if value and not isinstance(value, basestring):
            value = json.dumps(value)
        SessionRecord(
            ip_address=request.remote_addr or '',
            user_agent=request.user_agent.string[:1024],
            user=g.authorized.userid,
            value=value,
        ).save()
