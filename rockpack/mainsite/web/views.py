from urllib import urlencode
from urlparse import urljoin
from flask import request, json, render_template
from flask.ext import wtf
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
        # Make local in-process request at top of WSGI stack
        env = request.environ.copy()
        env['PATH_INFO'] = url
        env['QUERY_STRING'] = urlencode(kwargs)
        response = u''.join(app.wsgi_app(env, lambda status, headers: None))
        # TODO: Catch non-200 responses
    return json.loads(response)


@expose_web('/', 'web/home.html', cache_age=3600)
def homepage():
    pass


@expose_web('/bookmarklet', 'web/bookmarklet.html')
def bookmarklet():
    api_urls = ws_request('/ws/')
    return dict(api_urls = api_urls), 200, {'P3P': 'CP="CAO PSA OUR"'}

@expose_web('/injectorjs', 'web/injector.js')
def injector():
    return dict(abspath = app.config), ['ASSETS_URL']), 200


@expose_web('/channel/<slug>/<channelid>/', 'web/channel.html', cache_age=3600)
def channel(slug, channelid):
    channel_data = ws_request('/ws/-/channels/%s/' % channelid, size=40)
    selected_video = None
    if 'video' in request.args:
        for instance in channel_data['videos']['items']:
            if instance['id'] == request.args['video']:
                selected_video = instance
        # Not in the first 40 - try fetching separately:
        if not selected_video:
            video_data = ws_request(
                '/ws/-/channels/%s/videos/%s/' % (channelid, request.args['video']))
            if 'error' not in video_data:
                selected_video = video_data
    channel_data['canonical_url'] = url_for(
        'channel', slug=slugify(channel_data['title']) or '-', channelid=channelid)
    if selected_video:
        channel_data['canonical_url'] += '?video=' + selected_video['id']
    injectorUrl = url_for('injector')
    return dict(channel_data=channel_data, selected_video=selected_video, injectorUrl=injectorUrl)


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
    return 'OK', 200, [('Content-Type', 'text/plain')]


@app.errorhandler(500)
def server_error(error):
    message = getattr(error, 'message', str(error))
    if request.path.startswith('/ws/'):
        return JsonReponse(dict(error='internal_error', message=message), 500)
    else:
        return render_template('server_error.html', message=message), 500
