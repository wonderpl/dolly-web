from flask import Flask

#from rockpack.services.video import api

app = Flask(__name__)
app.secret_key = '456%4534345375gfd@#pfsef367tgu'


# Register blueprints
#app.register_blueprint(video_api.video)
#api.ChannelAPI(app, '')

import auth
import admin
auth.setup_auth(app)
admin.setup_admin(app)

# stick this in a config or somthing

SERVICES = ['video']

def import_services():
    from rockpack.core.webservice import WebService # TODO: move this, obviously
    services = []
    for s in SERVICES:
        import_name = s.join(['rockpack.services.', '.api'])
        api =  __import__(import_name, fromlist=['api'])
        for a in api.__dict__.itervalues():
            if (isinstance(a, type) and issubclass(a, WebService)
                    and a.__name__ != WebService.__name__):
                services.append(a)

    for s in services:
        app.logger.debug('loading service: {}'.format(s.__name__))
        s(app, s.endpoint)

import_services()
