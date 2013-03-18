import requests
from urlparse import urljoin
from flask import request, json, render_template
from flask.ext import wtf
from rockpack.mainsite import app
from rockpack.mainsite.core.token import parse_access_token
from rockpack.mainsite.core.webservice import secure_view, JsonReponse
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.services.oauth.api import record_user_event


def ws_request(url):
    ws_base_url = app.config.get('WEB_WS_SERVICE_URL')
    if ws_base_url:
        response = requests.get(urljoin(ws_base_url, url)).content
    else:
        # Make local in-process request at top of WSGI stack
        env = request.environ.copy()
        env['PATH_INFO'] = url
        response = ''.join(app.wsgi_app(env, lambda status, headers: None))
        # TODO: Catch non-200 responses
    return json.loads(response)


@app.route('/')
def homepage():
    return render_template('web/home.html')


@app.route('/channel/<slug>/<channelid>/')
def channel(slug, channelid):
    channel_data = ws_request('/ws/-/channels/%s/' % channelid)
    for instance in channel_data['videos']['items']:
        if instance['id'] == request.args.get('video'):
            channel_data['selected_instance'] = instance
    return render_template('web/channel.html', **channel_data)


class ResetPasswordForm(wtf.Form):
    token = wtf.HiddenField()
    password = wtf.PasswordField(validators=[wtf.Required(), wtf.Length(min=6)])
    password2 = wtf.PasswordField(validators=[wtf.Required(), wtf.Length(min=6)])

    def validate_password2(self, field):
        if not self.password.data == self.password2.data:
            raise wtf.ValidationError('Passwords must match.')


@app.route('/reset_password/', methods=('GET', 'POST'), subdomain=app.config.get('SECURE_SUBDOMAIN'))
@secure_view()
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
            user.set_password(form.password.data)
            user.save()
            record_user_event(user.username, 'password changed')
    return render_template('web/reset_password.html', **locals())


@app.errorhandler(500)
def server_error(error):
    message = getattr(error, 'message', str(error))
    if request.path.startswith('/ws/'):
        return JsonReponse(dict(error='internal_error', message=message), 500)
    else:
        return render_template('server_error.html', message=message), 500
