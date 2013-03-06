import requests
from urlparse import urljoin
from flask import request, json, render_template
from rockpack.mainsite import app


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
