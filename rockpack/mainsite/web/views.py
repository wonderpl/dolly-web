from urllib import urlencode
from urlparse import urljoin
import pyes
from flask import request, json, render_template, abort, redirect
from flask.ext import wtf
from werkzeug.http import HTTP_STATUS_CODES
from werkzeug.exceptions import NotFound
from rockpack.mainsite import app, requests
from rockpack.mainsite.core.token import parse_access_token
from rockpack.mainsite.core.webservice import JsonReponse
from rockpack.mainsite.helpers.urls import url_for, slugify
from rockpack.mainsite.helpers.http import cache_for
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.services.share.models import ShareLink
from rockpack.mainsite.services.oauth.api import record_user_event
from .decorators import expose_web


def ws_request(url, **kwargs):
    ws_base_url = app.config.get('WEB_WS_SERVICE_URL')
    if ws_base_url:
        response = requests.get(urljoin(ws_base_url, url), params=kwargs).content
    else:
        def start_response(status, headers):
            meta['status'] = status
            meta['headers'] = headers
        # Make local in-process request at top of WSGI stack
        env = request.environ.copy()
        env['PATH_INFO'] = url
        env['REQUEST_METHOD'] = 'GET'
        env['QUERY_STRING'] = urlencode(kwargs)
        if 'API_SUBDOMAIN' in app.config:
            env['HTTP_HOST'] = '.'.join((app.config['API_SUBDOMAIN'], app.config['SERVER_NAME']))
        meta = {}
        response = u''.join(app.wsgi_app(env, start_response))
        if meta['status'] == '404 NOT FOUND':
            abort(404)
    return json.loads(response)


@expose_web('/welcome_email', 'web/welcome_email.html', cache_age=3600)
def welcome_email():
    return None


@expose_web('/', 'web/home.html', cache_age=3600)
def homepage():
    api_urls = json.dumps(ws_request('/ws/'))
    return dict(api_urls=api_urls)


@expose_web('/fullweb', 'web/fullweb.html', cache_age=3600)
def fullweb():
    if app.config.get('ENABLE_FULLWEB', False):
        api_urls = json.dumps(ws_request('/ws/'))
        return dict(api_urls=api_urls)
    else:
        abort(404)


@expose_web('/bookmarklet', 'web/bookmarklet.html', cache_age=3600, secure=True)
def bookmarklet():
    api_urls = ws_request('/ws/')
    return dict(api_urls=api_urls), 200, {'P3P': 'CP="CAO PSA OUR"'}


@expose_web('/injectorjs', 'web/injector.js', cache_age=3600, secure=True)
def injector():
    return dict(iframe_url=url_for('bookmarklet')), 200, {'Content-Type': 'application/javascript'}


@expose_web('/tos', 'web/terms.html', cache_age=3600)
def terms():
    return {}


@expose_web('/cookies', 'web/cookies.html', cache_age=3600)
def cookies():
    return {}


@expose_web('/privacy', 'web/privacy.html', cache_age=3600)
def privacy():
    return {}


def web_channel_data(channelid, load_video=None):
    channel_data = ws_request('/ws/-/channels/%s/' % channelid, size=0)
    selected_video = None
    if load_video:
        for instance in channel_data['videos']['items']:
            if instance['id'] == load_video:
                selected_video = instance
        # Not in the first 40 - try fetching separately:
        if not selected_video:
            try:
                video_data = ws_request(
                    '/ws/-/channels/%s/videos/%s/' % (channelid, load_video))
            except NotFound:
                pass
            else:
                if 'error' not in video_data:
                    selected_video = video_data
    channel_data['canonical_url'] = url_for(
        'channel', slug=slugify(channel_data['title']) or '-', channelid=channelid)
    if selected_video:
        channel_data['canonical_url'] += '?video=' + selected_video['id']
    return dict(channel_data=channel_data, selected_video=selected_video)


def share_link_processing(linkid):
    not_social_bot = True
    show_meta_only = False
    if filter(lambda x: x in request.user_agent.string.lower(), ('twitter', 'facebookexternalhit',)):
        not_social_bot = False
        show_meta_only = True

    link = ShareLink.query.get_or_404(linkid)
    data = link.process_redirect(increment_click_count=not_social_bot)

    if show_meta_only:
        return render_template(
            'web/social_agents.html',
            short_url=url_for('share_redirect', linkid=linkid),
            **web_channel_data(
                data.get('channel'),
                load_video=data.get('video')
            )
        )
    return redirect(data.get('url'), 302)


@expose_web('/channel/<slug>/<channelid>/', 'web/channel.html', cache_age=3600)
def channel(slug, channelid):
    return web_channel_data(channelid, load_video=request.args.get('video', None))


if app.config.get('SHARE_SUBDOMAIN'):
    @app.route('/s/<linkid>')
    def old_share_redirect(linkid):
        return redirect(url_for('share_redirect', linkid=linkid), 301)


@cache_for(seconds=86400, private=True)
@app.route('/s/<linkid>', subdomain=app.config.get('SHARE_SUBDOMAIN'))
def share_redirect(linkid):
    return share_link_processing(linkid)


class ResetPasswordForm(wtf.Form):
    token = wtf.HiddenField()
    password = wtf.PasswordField('NEW PASSWORD', validators=[wtf.Required(), wtf.Length(min=6)])
    password2 = wtf.PasswordField('RETYPE NEW PASSWORD', validators=[wtf.Required(), wtf.Length(min=6)])

    def validate_password2(self, field):
        if not self.password.data == self.password2.data:
            raise wtf.ValidationError('Passwords must match.')


@expose_web('/reset_password/', 'web/reset_password.html', methods=('GET', 'POST'), secure=True)
def reset_password():
    token = (request.form or request.args).get('token')
    try:
        userid, clientid = parse_access_token(str(token))
    except TypeError:
        pass
    else:
        form = ResetPasswordForm(token=token)
        if form.validate_on_submit():
            user = User.query.get(userid)
            user.change_password(user, form.password.data)
            record_user_event(user.username, 'password changed')
    return locals()


@app.route('/status/', subdomain='<sub>')
def status(sub):
    es_url = app.config.get('ELASTICSEARCH_URL')
    if es_url:
        assert pyes.ES(es_url).status()['ok']
    return 'OK', 200, [('Content-Type', 'text/plain')]


@app.errorhandler(404)
def not_found(error):
    return handle_error(404, error, '400_error.html')


@app.errorhandler(500)
def server_error(error):
    return handle_error(500, error, '500_error.html')


def handle_error(code, error, template):
    message = str(getattr(error, 'message', error))
    if request.path.startswith('/ws/'):
        return JsonReponse(dict(error=HTTP_STATUS_CODES[code], message=message), code)
    else:
        return render_template(template, message=message), code
