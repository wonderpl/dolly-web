from datetime import datetime
import wtforms as wtf
from flask import abort, g
from flask.ext.wtf import Form
from sqlalchemy.orm.exc import NoResultFound
from rockpack.mainsite import app
from rockpack.mainsite.core import email
from rockpack.mainsite.core.webservice import WebService, expose_ajax, ajax_create_response
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.services.user.commands import complex_push_notification, get_apns_token
from rockpack.mainsite.services.video.models import Channel, VideoInstance
from rockpack.mainsite.services.user.api import save_video_activity
from rockpack.mainsite.services.user.models import EXTERNAL_SYSTEM_NAMES, User
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
    channel='pack'
)


def send_share_email(recipient, user, object_type, object, link):
    object_type_name = OBJECT_NAME_MAP[object_type]
    subject = '%s shared a %s with you on Rockpack' % (user.display_name, object_type_name)
    template = email.env.get_template('share.html')
    assets_url = app.config.get('ASSETS_URL', '')
    if assets_url.startswith('//'):
        # Force https for static images in html email (seems to be needed by yahoo mail)
        assets_url = 'https:' + assets_url
    body = template.render(
        user=user,
        link=link,
        object_type=object_type,
        object_type_name=object_type_name,
        object=object,
        assets=assets_url,
    )
    email.send_email(recipient, subject, body, format='html')

    try:
        recipient_user = User.query.filter(User.email.ilike(recipient.lower())).one()
        token = get_apns_token(recipient_user.id)
        if token:
            msg_func = {'video': lambda video_instance: video_instance.resource_url,
                    'channel': lambda channel: channel.cover.thumbnail_medium}

            push_message = '%@ shared a ' + object_type_name + ' with you'
            push_message_args = [user.display_name]
            deeplink_url = msg_func[object_type_name]
            complex_push_notification(token, push_message, push_message_args, url=deeplink_url)
    except NoResultFound:
        pass


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
        link = ShareLink.create(g.authorized.userid, form.object_type.data, form.object_id.data)
        send_share_email(form.email.data, g.authorized.user, form.object_type.data, form.object, link)
