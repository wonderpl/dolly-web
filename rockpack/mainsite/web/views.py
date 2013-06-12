from urllib import urlencode
from urlparse import urljoin
import pyes
from flask import request, json, render_template, abort
from flask.ext import wtf
from werkzeug.exceptions import NotFound
from rockpack.mainsite import app, requests
from rockpack.mainsite.core.token import parse_access_token
from rockpack.mainsite.core.webservice import JsonReponse
from rockpack.mainsite.helpers.urls import url_for, slugify
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
        env['QUERY_STRING'] = urlencode(kwargs)
        if 'API_SUBDOMAIN' in app.config:
            env['HTTP_HOST'] = '.'.join((app.config['API_SUBDOMAIN'], app.config['SERVER_NAME']))
        meta = {}
        response = u''.join(app.wsgi_app(env, start_response))
        if meta['status'] == '404 NOT FOUND':
            abort(404)
    return json.loads(response)


@expose_web('/', 'web/home.html', cache_age=3600)
def homepage():
    api_urls = json.dumps(ws_request('/ws/'))
    return dict(api_urls=api_urls)


@expose_web('/bookmarklet', 'web/bookmarklet.html', cache_age=3600, secure=True)
def bookmarklet():
    api_urls = ws_request('/ws/')
    return dict(api_urls=api_urls), 200, {'P3P': 'CP="CAO PSA OUR"'}


@expose_web('/injectorjs', 'web/injector.js', cache_age=3600, secure=True)
def injector():
    return dict(iframe_url=url_for('bookmarklet')), 200, {'Content-Type': 'application/javascript'}


@expose_web('/tos', 'web/terms.html', cache_age=3600)
def terms():
    return dict(full_site=postlaunch_path)


@expose_web('/cookies', 'web/cookies.html', cache_age=3600)
def cookies():
    return dict(full_site=postlaunch_path)


@expose_web('/privacy', 'web/privacy.html', cache_age=3600)
def privacy():
    return dict(full_site=postlaunch_path)


@expose_web('/channel/<slug>/<channelid>/', 'web/channel.html', cache_age=3600)
def channel(slug, channelid):
    #Temporary fix to pagination bug, fetching 1000 videos.
    channel_data = ws_request('/ws/-/channels/%s/' % channelid, size=1000)
    selected_video = None
    if 'video' in request.args:
        for instance in channel_data['videos']['items']:
            if instance['id'] == request.args['video']:
                selected_video = instance
        # Not in the first 40 - try fetching separately:
        if not selected_video:
            try:
                video_data = ws_request(
                    '/ws/-/channels/%s/videos/%s/' % (channelid, request.args['video']))
            except NotFound:
                pass
            else:
                if 'error' not in video_data:
                    selected_video = video_data
    channel_data['canonical_url'] = url_for(
        'channel', slug=slugify(channel_data['title']) or '-', channelid=channelid)
    if selected_video:
        channel_data['canonical_url'] += '?video=' + selected_video['id']
    return dict(channel_data=channel_data, selected_video=selected_video, full_site=postlaunch_path)


@expose_web('/s/<linkid>', cache_age=60, cache_private=True)
def share_redirect(linkid):
    link = ShareLink.query.get_or_404(linkid)
    return None, 302, {'Location': link.process_redirect()}


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
    # TODO: some internal checks
    es = pyes.ES(app.config.get('ELASTICSEARCH_URL'))
    assert es.status()['ok']
    return 'OK', 200, [('Content-Type', 'text/plain')]


@app.errorhandler(500)
def server_error(error):
    message = getattr(error, 'message', str(error))
    if request.path.startswith('/ws/'):
        return JsonReponse(dict(error='internal_error', message=message), 500)
    else:
        return render_template('server_error.html', message=message), 500
