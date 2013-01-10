from flask import Flask
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqlamodel import ModelView

from rockpack.core.dbapi import session
from rockpack.services.video import models as video_models
from rockpack.services.video import api as video_api

app = Flask(__name__)
app.secret_key = '456%4534345375gfd@#pfsef367tgu'

# Admin stuff

admin = Admin(app, name='Rockpack Admin')
admin.add_view(ModelView(video_models.Video, session))
admin.add_view(ModelView(video_models.VideoInstance, session))
admin.add_view(ModelView(video_models.VideoSource, session))
admin.add_view(ModelView(video_models.Category, session))
admin.add_view(ModelView(video_models.Locale, session))
admin.add_view(ModelView(video_models.Channel, session))

# Register blueprints
app.register_blueprint(video_api.video)


