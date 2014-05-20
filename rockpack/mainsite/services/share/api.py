from datetime import datetime
import urlparse
import wtforms as wtf
from sqlalchemy import func
from flask import abort, g, json
from flask.ext.wtf import Form
from rockpack.mainsite import app
from rockpack.mainsite.core import email
from rockpack.mainsite.core.webservice import WebService, expose_ajax, ajax_create_response
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.background_sqs_processor import background_on_sqs
from rockpack.mainsite.services.user import commands
from rockpack.mainsite.services.video.models import Channel, Video, VideoInstance
from rockpack.mainsite.services.user.api import save_video_activity
from rockpack.mainsite.services.user.models import EXTERNAL_SYSTEM_NAMES, User, UserNotification
from rockpack.mainsite.services.search.api import VIDEO_INSTANCE_PREFIX
from rockpack.mainsite.services.oauth.models import ExternalFriend
from rockpack.mainsite.services.oauth.api import email_validator
from .models import ShareLink


SHARE_OBJECT_TYPE_MAP = dict(
    channel=Channel,
    video_instance=VideoInstance,
)

OBJECT_NAME_MAP = dict(
    video_instance='video',
    channel='collection' if app.config.get('DOLLY') else 'pack'
)


@background_on_sqs
def share_content(userid, object_type, object_id, recipient_email):
    link = ShareLink.create(userid, object_type, object_id)
    object = SHARE_OBJECT_TYPE_MAP[object_type].query.get(object_id)
    user = User.query.get(userid)

    # Send email
    template = email.env.get_template('share.html')
    if app.config.get('DOLLY') and object_type == 'channel':
        top_videos = VideoInstance.query.filter_by(channel=object.id).\
            join(Video, (Video.id == VideoInstance.video) & (Video.visible == True)).\
            order_by(VideoInstance.position, VideoInstance.date_added.desc()).limit(3)
    else:
        top_videos = []
    body = template.render(
        recipient=recipient_email,
        user=user,
        link=link,
        object_type=object_type,
        object_type_name=OBJECT_NAME_MAP[object_type],
        object=object,
        top_videos=top_videos,
    )
    email.send_email(recipient_email, body)

    recipient_user = User.query.filter(func.lower(User.email) == recipient_email.lower()).first()
    if recipient_user:
        # Create user notification
        message_body = dict(user=commands._notification_user_info(user))
        if object_type == 'channel':
            message_body['channel'] = commands._notification_channel_info(object, own=False)
            message_type = 'channel_shared'
        else:
            message_body['video'] = commands._notification_video_info(object, object.video_channel)
            message_type = 'video_shared'
        UserNotification(
            user=recipient_user.id,
            date_created=link.date_created,
            message_type=message_type,
            message=json.dumps(message_body, separators=(',', ':')),
        ).save()

        # Send push notification
        token = commands.get_apns_token(recipient_user.id)
        if token:
            push_message = '%@ shared a ' + OBJECT_NAME_MAP[object_type] + ' with you'
            push_message_args = [user.display_name]
            deeplink_url = urlparse.urlparse(object.resource_url).path.lstrip('/ws/')
            commands.complex_push_notification(token, push_message, push_message_args, url=deeplink_url)


class ShareForm(Form):
    object_type = wtf.SelectField(choices=SHARE_OBJECT_TYPE_MAP.items())
    object_id = wtf.StringField(validators=[wtf.validators.Required()])

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

            self.object = object_type.query.filter_by(id=field.data).first()
            if not self.object:
                raise wtf.ValidationError('invalid id')

    def get_message_map(self):
        type = self.object_type.data
        ctx = dict(
            title=(self.object.video_rel.title if type == 'video_instance'
                   else self.object.title),
        )
        return dict((k, v.format(ctx))
                    for k, v in app.config['SHARE_MESSAGE_MAP'][type].iteritems())


class EmailShareForm(ShareForm):
    email = wtf.StringField(validators=[wtf.validators.Required(), wtf.validators.Email(), email_validator()])
    name = wtf.StringField()
    _external_system_choices = zip(EXTERNAL_SYSTEM_NAMES, map(str.capitalize, EXTERNAL_SYSTEM_NAMES))
    external_system = wtf.SelectField(choices=_external_system_choices, validators=[wtf.validators.Optional()])
    external_uid = wtf.StringField()


class ShareWS(WebService):

    endpoint = '/share'

    @expose_ajax('/link/', methods=['POST'], secure=True)
    @check_authorization()
    def create_share_link(self):
        form = ShareForm(csrf_enabled=False, user=g.authorized.userid, locale=self.get_locale())
        if not form.validate():
            abort(400, form_errors=form.errors)
        link = ShareLink.create(g.authorized.userid, form.object_type.data, form.object_id.data)
        return ajax_create_response(link, form.get_message_map())

    @expose_ajax('/email/', methods=['POST'], secure=True)
    @check_authorization()
    def email_share(self):
        form = EmailShareForm(csrf_enabled=False, user=g.authorized.userid, locale=self.get_locale())
        if not form.validate():
            abort(400, form_errors=form.errors)
        if form.external_uid.data:
            # Update email & name fields on existing friend record or create new record
            friendkey = dict(
                user=g.authorized.userid,
                external_system=form.external_system.data,
                external_uid=form.external_uid.data,
            )
            friendval = dict(
                email=form.email.data,
                last_shared_date=datetime.utcnow(),
            )
            if form.name.data:
                friendval['name'] = form.name.data
            updated = ExternalFriend.query.filter_by(**friendkey).update(friendval)
            if not updated and form.external_system.data == 'email':
                ExternalFriend(**dict(friendkey, **friendval)).save()
        share_content(g.authorized.userid, form.object_type.data, form.object_id.data, form.email.data)
