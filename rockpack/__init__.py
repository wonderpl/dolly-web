from flask import Flask

from rockpack.services.video import api

app = Flask(__name__)
app.secret_key = '456%4534345375gfd@#pfsef367tgu'


# Register blueprints
#app.register_blueprint(video_api.video)
api.ChannelAPI(app, '')

import auth
import admin
auth.setup_auth(app)
admin.setup_admin(app)

