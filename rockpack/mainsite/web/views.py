from flask import request, json, render_template
from rockpack.mainsite import app


def ws_request(url):
    def start_response(status, headers):
        pass
    env = request.environ.copy()
    env['PATH_INFO'] = url
    response = ''.join(app.wsgi_app(env, start_response))
    return json.loads(response)


@app.route('/')
def homepage():
    return render_template('web/home.html')


@app.route('/channel/<slug>/<channelid>/')
def channel(slug, channelid):
    channel_data = ws_request('/ws/-/channels/%s/' % channelid)
    return render_template('web/channel.html', **channel_data)
