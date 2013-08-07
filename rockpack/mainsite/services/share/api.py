from collections import defaultdict
from flask import abort, g
from flask.ext import wtf
from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import WebService, expose_ajax, ajax_create_response
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.services.video.models import Channel, VideoInstance
from rockpack.mainsite.services.user.api import save_video_activity
from rockpack.mainsite.services.search.api import VIDEO_INSTANCE_PREFIX
from .models import ShareLink


SHARE_OBJECT_TYPE_MAP = dict(
    channel=Channel,
    video_instance=VideoInstance,
)


class ShareForm(wtf.Form):
    object_type = wtf.SelectField(choices=SHARE_OBJECT_TYPE_MAP.items())
    object_id = wtf.StringField(validators=[wtf.Required()])

    def __init__(self, user=None, locale=None, *args, **kwargs):
        self._user = user
        self._locale = locale
        super(ShareForm, self).__init__(*args, **kwargs)

    def validate_object_id(self, field):
        object_type = SHARE_OBJECT_TYPE_MAP.get(self.object_type.data)
        if object_type:
            if field.data.startswith(VIDEO_INSTANCE_PREFIX):
                # This is a video from search - we need to create a new
                # video instance in the user's favourites channel
                instance = save_video_activity(self._user, 'star', field.data, self._locale)
                field.data = getattr(instance, 'id', instance)

            object = object_type.query.filter_by(id=field.data).first()
            if not object:
                raise wtf.ValidationError('invalid id')
            message_fmt = app.config.get('SHARE_MESSAGE_MAP', {})

            kw = defaultdict(str)
            if self.object_type.data == 'video_instance':
                kw['object_type'] = self.object_type.data
                kw['title'] = object.video.title
            else:
                kw['object_type'] = self.object_type.data
                kw['title'] = object.title

            for key, val in message_fmt.iteritems():
                try:
                    setattr(self, key, val.format(kw))
                except KeyError:
                    setattr(self, key, '')


class ShareWS(WebService):

    endpoint = '/share'

    @expose_ajax('/link/', methods=['POST'], secure=True)
    @check_authorization()
    def create_share_link(self):
        form = ShareForm(csrf_enabled=False, user=g.authorized.userid, locale=self.get_locale())
        if not form.validate():
            abort(400, form_errors=form.errors)
        link = ShareLink.create(
            g.authorized.userid, form.object_type.data, form.object_id.data)
        msg_dict = dict(
            message=form.message,
            message_facebook=form.facebook,
            message_twitter=form.twitter,
            message_email=form.email,
        )
        return ajax_create_response(link, msg_dict)
