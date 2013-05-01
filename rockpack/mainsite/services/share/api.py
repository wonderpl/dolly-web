from flask import abort, g
from flask.ext import wtf
from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import WebService, expose_ajax, ajax_create_response
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.services.video.models import Channel, VideoInstance
from .models import ShareLink


SHARE_OBJECT_TYPE_MAP = dict(
    channel=Channel,
    video_instance=VideoInstance,
)


class ShareForm(wtf.Form):
    object_type = wtf.SelectField(choices=SHARE_OBJECT_TYPE_MAP.items())
    object_id = wtf.StringField(validators=[wtf.Required()])

    def validate_object_id(self, field):
        object_type = SHARE_OBJECT_TYPE_MAP.get(self.object_type.data)
        if object_type:
            object = object_type.query.filter_by(id=field.data).first()
            if not object:
                raise wtf.ValidationError('invalid id')
            message_fmt = app.config.get('SHARE_MESSAGE_MAP', {}).get(self.object_type.data)
            self.message = message_fmt and message_fmt.format(object=object)


class ShareWS(WebService):

    endpoint = '/share'

    @expose_ajax('/link/', methods=['POST'], secure=True)
    @check_authorization()
    def create_share_link(self):
        form = ShareForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)
        link = ShareLink.create(
            g.authorized.userid, form.object_type.data, form.object_id.data)
        return ajax_create_response(link, dict(message=form.message))
