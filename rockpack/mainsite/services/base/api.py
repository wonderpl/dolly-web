from flask import request, url_for
from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import WebService, expose_ajax


class BaseService(WebService):

    endpoint = '/'

    @expose_ajax('/', cache_age=60)
    def discover(self):
        locale = request.args.get('locale', app.config['ENABLED_LOCALES'][0])
        return dict(
            popular_videos=url_for('ChannelAPI_api.channel_list', locale=locale, _external=True),
            login=url_for('Login_api.login', _external=True),
        )
