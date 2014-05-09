import re
from urllib import urlencode
from urlparse import urljoin, parse_qs, urlsplit, urlunsplit
from cStringIO import StringIO
import pyes
import wtforms as wtf
from flask import request, json, render_template, abort, redirect
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileRequired
from werkzeug.http import HTTP_STATUS_CODES
from werkzeug.exceptions import NotFound
from rockpack.mainsite import app, requests
from rockpack.mainsite.core.token import parse_access_token, parse_unsubscribe_token
from rockpack.mainsite.core.webservice import JsonReponse
from rockpack.mainsite.helpers.urls import url_for, slugify
from rockpack.mainsite.helpers.http import cache_for
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.services.share.models import ShareLink
from rockpack.mainsite.services.oauth.api import record_user_event
from .decorators import expose_web, iframe_proxy_redirect


def ws_request(url, method='GET', content_type=None, body=None, token=None, **kwargs):
    ws_base_url = app.config.get('WEB_WS_SERVICE_URL')
    if ws_base_url:
        response = requests.get(urljoin(ws_base_url, url), params=kwargs).content
    else:
        def start_response(status, headers):
            meta['status'] = status
            meta['headers'] = headers
        # Make local in-process request at top of WSGI stack
        env = request.environ.copy()
        if content_type:
            env['CONTENT_TYPE'] = content_type
        if body:
            env['CONTENT_LENGTH'] = len(body)
            env['wsgi.input'] = StringIO(body)
        env['PATH_INFO'] = url
        env['REQUEST_METHOD'] = method
        env['QUERY_STRING'] = urlencode(kwargs)
        if token:
            env['HTTP_AUTHORIZATION'] = 'Bearer %s' % str(token)
        if not token and 'API_SUBDOMAIN' in app.config:
            env['HTTP_HOST'] = '.'.join((app.config['API_SUBDOMAIN'], app.config['SERVER_NAME']))
        meta = {}
        response = u''.join(app.wsgi_app(env, start_response))
        if meta['status'] == '404 NOT FOUND':
            abort(404)
    return response and json.loads(response)


def romeo_ws_request(url):
    ws_base_url = app.config['ROMEO_WS_URL']
    response = requests.get(urljoin(ws_base_url, url))
    if response.status_code == 404:
        abort(404)
    return response.json()


@expose_web('/welcome_email', cache_age=3600)
def welcome_email():
    from rockpack.mainsite.core.email import env
    return env.get_template('welcome.html').render(web=True)


@expose_web('/', 'web/home.html', cache_age=3600)
def homepage():
    api_urls = json.dumps(ws_request('/ws/'))
    channels = ws_request('/ws/channels/', size=8)
    return dict(api_urls=api_urls, injectorUrl=url_for('injector'), top_channels=channels)

if app.config.get('SECURE_SUBDOMAIN'):
    app.add_url_rule('/', 'secure_home_redirect',
                     lambda: redirect(url_for('homepage')), subdomain=app.config['SECURE_SUBDOMAIN'])

if app.config.get('ADMIN_SUBDOMAIN'):
    app.add_url_rule('/', 'admin_redirect',
                     lambda: redirect('/admin/'), subdomain=app.config['ADMIN_SUBDOMAIN'])


@expose_web('/fullweb', 'web/fullweb.html', cache_age=3600)
def fullweb():
    if app.config.get('ENABLE_FULLWEB', False):
        api_urls = json.dumps(ws_request('/ws/'))
        return dict(api_urls=api_urls)
    else:
        abort(404)


class FileUploadForm(Form):
    user = wtf.HiddenField(validators=[wtf.validators.Required()])
    token = wtf.HiddenField(validators=[wtf.validators.Required()])
    file = wtf.FileField(validators=[wtf.validators.Required(), FileRequired()])


@app.route('/upload/<any("avatar", "cover_art"):type>', methods=['POST'], subdomain=app.config.get('SECURE_SUBDOMAIN'))
@iframe_proxy_redirect()
def fileupload(type):
    form = FileUploadForm(csrf_enabled=False)
    if not form.validate_on_submit():
        return dict(error='invalid_request', form_errors=form.errors)
    ws_url = '/ws/%s/%s/' % (form.user.data, type)
    method = 'PUT' if type == 'avatar' else 'POST'
    body = form.file.data.stream.read()
    return ws_request(ws_url, method, 'image/unknown', body, form.token.data)


@expose_web('/iframe_proxy', 'web/iframe_proxy.html')
def iframe_proxy():
    callback = request.args.get('_callback', 'alert')
    result = request.args.get('result', '[]')
    if not result.startswith('['):
        result = '[%s]' % result    # javascript argument must be a list
    return dict(
        callback=callback,
        callback_base='.'.join(callback.split('.')[0:-1]),
        result=result,
    )


@expose_web('/bookmarklet', 'web/bookmarklet.html', cache_age=3600, secure=True)
def bookmarklet():
    api_urls = ws_request('/ws/')
    return dict(api_urls=api_urls), 200, {'P3P': 'CP="CAO PSA OUR"'}


@expose_web('/injectorjs', 'web/injector.js', cache_age=3600, secure=True)
def injector():
    return dict(iframe_url=url_for('bookmarklet')), 200, {'Content-Type': 'application/javascript'}


@expose_web('/hints', 'web/hints.html', cache_age=3600)
def hints():
    return {}


@expose_web('/help', 'web/help.html', cache_age=3600)
def help():
    return {}


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
    channel_data = ws_request('/ws/-/channels/%s/' % channelid, size=40)
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
    return dict(channel_data=channel_data, selected_video=selected_video, api_urls=json.dumps(ws_request('/ws/')))


@expose_web('/channel/<slug>/<channelid>/', 'web/channel.html', cache_age=3600)
def channel(slug, channelid):
    videoid = request.args.get('video', None)
    return web_channel_data(channelid, load_video=videoid)


@expose_web('/embed/<contentid>/', 'web/embed.html', cache_age=3600, secure='both')
def embed(contentid):
    if app.config.get('DOLLY'):
        if contentid.startswith('vi'):
            return dict(video_data=ws_request('/ws/-/channels/-/videos/%s/' % contentid))
        else:
            try:
                int(contentid)
            except Exception:
                abort(404)
            else:
                return dict(video_data=romeo_ws_request('/api/v/%s' % contentid))
    else:
        videoid = request.args.get('video', None)
        return web_channel_data(contentid, load_video=videoid)


def _update_qs(url, dict_):
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)
    query_params.update(dict_)
    new_query_string = urlencode(query_params, doseq=True)
    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


def _rockpack_protocol_url(url):
    """Convert a web url to a rockpack protocol ws url."""
    channel_match = re.search('ch[\w-]{22}', url)
    if channel_match:
        video_match = re.search('vi[\w-]{22}', url)
        url = '{}://-/channels/{}/{}'.format(
            app.config['IOS_APP_URL_SCHEME'],
            channel_match.group(),
            'video/{}/'.format(video_match.group()) if video_match else '')
    return url


def _share_redirect(data):
    # Add additional query params to url
    pt_params = app.config.get('SHARE_REDIRECT_PASSTHROUGH_PARAMS', [])
    params = [(k, request.args[k]) for k in pt_params if k in request.args]
    if 'user' in data:
        params.append(('shareuser', data['user']))
    ua_str = request.user_agent.string
    if (app.config['MOBILE_BROWSER_RE1'].search(ua_str) or
            app.config['MOBILE_BROWSER_RE2'].search(ua_str[:4])):
        params.append(('mobile', 'true'))
    redirect_url = _update_qs(data['url'], params)

    if request.args.get('rockpack_redirect') == 'true':
        return redirect(_rockpack_protocol_url(redirect_url), 302)

    if data.get('social_bot'):
        return render_template(
            'web/social_agents.html',
            canonical_url=data['share_url'],
            **web_channel_data(data['channel'], load_video=data.get('video'))
        )

    if request.user_agent.platform == 'ios' or request.args.get('interstitial') == 'true':
        return render_template(
            'web/app_interstitial.html',
            redirect_url=redirect_url,
            protocol_url=_rockpack_protocol_url(redirect_url),
        )

    return redirect(redirect_url, 302)


if app.config.get('SHARE_SUBDOMAIN'):
    @app.route('/s/<linkid>', subdomain=app.config.get('DEFAULT_SUBDOMAIN'))
    def old_share_redirect(linkid):
        return redirect(url_for('share_redirect', linkid=linkid), 301)


@app.route('/s', subdomain=app.config.get('SHARE_SUBDOMAIN'))
@cache_for(seconds=86400, private=True, vary='User-Agent')
def share_redirect_root():
    channel, video = request.args.get('c'), request.args.get('v')
    if not channel:
        abort(404)
    url = url_for('channel', slug='-', channelid=channel)
    if video:
        url += '?video=' + video
    share_url = url_for('share_redirect_root') + '?c=%s&v=%s' % (channel, video)
    return _share_redirect(locals())


@app.route('/s/<linkid>', subdomain=app.config.get('SHARE_SUBDOMAIN'))
@cache_for(seconds=86400, private=True, vary='User-Agent')
def share_redirect(linkid):
    link = ShareLink.query.get_or_404(linkid)
    social_bot = any(ua in request.user_agent.string.lower()
                     for ua in ('twitterbot', 'facebookexternalhit'))
    data = link.process_redirect(increment_click_count=not social_bot)
    data.update(
        social_bot=social_bot,
        share_url=url_for('share_redirect', linkid=linkid),
    )
    return _share_redirect(data)


class ResetPasswordForm(Form):
    token = wtf.HiddenField()
    password = wtf.PasswordField('NEW PASSWORD', validators=[wtf.validators.Required(), wtf.validators.Length(min=6)])
    password2 = wtf.PasswordField('RETYPE NEW PASSWORD', validators=[wtf.validators.Required(), wtf.validators.Length(min=6)])

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
            record_user_event(user.username, 'password changed', user=user)
            user.save()
    return locals()


@expose_web('/unsubscribe/', 'web/unsubscribe.html', secure=True)
def unsubscribe():
    token = request.args.get('token')
    try:
        listid, userid = parse_unsubscribe_token(str(token))
    except TypeError:
        return dict(error='Invalid token')
    else:
        user = User.query.filter_by(id=userid).first()
        if user:
            user.set_flag('unsub%d' % listid)
            user.save()
            return dict(email=user.email)


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
