from sqlalchemy import desc
from flask import abort, request, g
from flask.ext import wtf
from flask.ext.admin import form
from wtforms.validators import ValidationError
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.webservice import WebService, expose_ajax, ajax_create_response, process_image
from rockpack.mainsite.core.oauth.decorators import check_authorization
from rockpack.mainsite.core.youtube import get_video_data
from rockpack.mainsite.helpers.db import gen_videoid, resize_and_upload
from rockpack.mainsite.services.video.models import (
    Channel, Video, VideoInstance, VideoLocaleMeta, Category)
from rockpack.mainsite.services.cover_art.models import UserCoverArt, RockpackCoverArt
from rockpack.mainsite.services.cover_art import api as cover_api
from rockpack.mainsite.services.video import api as video_api
from rockpack.mainsite.services.search import api as search_api
from .models import User, UserActivity


ACTION_COLUMN_VALUE_MAP = dict(
    view=('view_count', 1),
    star=('star_count', 1),
    unstar=('star_count', -1),
)


def get_or_create_video_record(search_instance_id, locale):
    try:
        prefix, source, source_videoid = search_instance_id.split('-', 2)
        source = int(source)
    except ValueError:
        abort(400)
    assert source == 1
    video_id = gen_videoid(None, source, source_videoid)
    if not Video.query.filter_by(id=video_id).count():
        video_data = get_video_data(source_videoid)
        Video.add_videos(video_data.videos, source, locale)
    return video_id


@commit_on_success
def save_video_activity(user, action, instance_id, locale):
    try:
        column, value = ACTION_COLUMN_VALUE_MAP[action]
    except KeyError:
        abort(400, message='invalid action')

    instance = VideoInstance.query.filter_by(id=instance_id)
    if instance_id.startswith(search_api.VIDEO_INSTANCE_PREFIX):
        video_id = get_or_create_video_record(instance_id, locale)
    else:
        video_id = instance.value(VideoInstance.video)
        if not video_id:
            abort(400, message='video_instance not found')

    if action == 'view':
        object_type = 'video_instance'
        object_id = instance_id
    else:
        object_type = 'video'
        object_id = video_id

    activity = dict(user=user, action=action,
                    object_type=object_type, object_id=object_id)
    if not UserActivity.query.filter_by(**activity).count():
        # Increment value on each of instance, video, & locale meta
        video = Video.query.filter_by(id=video_id)
        meta = VideoLocaleMeta.query.filter_by(video=video_id, locale=locale)
        incr = lambda m: {getattr(m, column): getattr(m, column) + value}
        instance.update(incr(VideoInstance))
        updated = video.update(incr(Video))
        assert updated
        updated = meta.update(incr(VideoLocaleMeta))
        if not updated:
            meta = Video.query.get(video_id).add_meta(locale)
            setattr(meta, column, 1)

    UserActivity(**activity).save()

    if action in ('star', 'unstar'):
        channel = Channel.query.filter_by(
            owner=user, title=app.config['FAVOURITE_CHANNEL'][0]).first()
        if channel:
            if action == 'unstar':
                channel.remove_videos([object_id])
            else:
                channel.add_videos([object_id])


def action_object_list(user, action, limit):
    query = UserActivity.query.filter_by(user=user, action=action).\
        order_by(desc('id')).limit(limit)
    id_list = zip(*query.values('object_id'))
    return id_list[0] if id_list else []


def check_present(form, field):
    if field.name not in (request.json or request.form):
        raise ValidationError('This field is required, but can be an empty string.')


def verify_id_on_model(model, col='id'):
    def f(form, field):
        if field.data:
            if not model.query.filter_by(**{col: field.data}).count():
                raise ValidationError('Invalid {} "{}"'.format(field, field.data))
    return f


class ChannelForm(form.BaseForm):
    title = wtf.TextField(validators=[check_present])
    description = wtf.TextField(validators=[check_present])
    category = wtf.TextField(validators=[check_present, verify_id_on_model(Category)])
    cover = wtf.TextField(validators=[check_present])

    def validate_cover(self, field):
        exists = lambda m: m.query.filter_by(cover=field.data).count()
        if field.data and not (exists(RockpackCoverArt) or exists(UserCoverArt)):
            raise ValidationError('invalid cover reference')

    def validate_title(self, field):
        user_channels = Channel.query.filter_by(owner=self.userid)
        if not field.data:
            untitled_channel = app.config['UNTITLED_CHANNEL'] + ' '
            count = user_channels.filter(Channel.title.like(untitled_channel + '%')).count()
            field.data = untitled_channel + str(count + 1)
        if user_channels.filter_by(title=field.data).count():
            raise ValidationError('duplicate title')


class UserAPI(WebService):

    endpoint = '/'

    @expose_ajax('/<userid>/', cache_age=60, cache_private=True)
    @check_authorization(abort_on_fail=False)
    def user_info(self, userid):
        user = User.query.get_or_404(userid)
        channels = Channel.query.filter_by(owner=user.id)
        if not g.authorized.userid == userid:
            channels = channels     # TODO: .filter_by(public=True)
        # TODO: Use secure resource_urls when owner is accessing
        channels = [video_api.channel_dict(c, with_owner=False) for c in user.channels]
        # TODO: Include additional personal info like email when owner?
        return dict(
            name=user.username,
            display_name=user.display_name,
            avatar_thumbnail_url=user.avatar.thumbnail_small,
            channels=channels,
        )

    # TODO: hack for recent videos. do this properly
    @expose_ajax('/<userid>/subscriptions/recent_videos/', cache_age=60, cache_private=True)
    def recent_videos(self, userid):
        data, total = video_api.get_local_videos(self.get_locale(), self.get_page(), date_order=True, **request.args)
        return {'videos': {'items': data, 'total': total}}

    @expose_ajax('/<userid>/activity/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_activity(self, userid):
        return dict(
            recently_viewed=action_object_list(userid, 'view', self.max_page_size),
            recently_starred=action_object_list(userid, 'star', self.max_page_size),
            subscribed=[],
        )

    @expose_ajax('/<userid>/activity/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_activity(self, userid):
        save_video_activity(userid,
                            request.form['action'],
                            request.form['video_instance'],
                            self.get_locale())

    @expose_ajax('/<userid>/channels/', methods=('POST',))
    @check_authorization(self_auth=True)
    def channel_item_create(self, userid):
        form = ChannelForm(csrf_enabled=False)
        form.userid = g.authorized.userid
        if not form.validate():
            abort(400, form_errors=form.errors)
        channel = Channel.create(
            owner=form.userid,
            title=form.title.data,
            description=form.description.data,
            cover=form.cover.data,
            category=form.category.data,
            locale=request.args.get('locale'))
        return ajax_create_response(channel)

    @expose_ajax('/<userid>/channels/<channelid>/', cache_age=0)
    @check_authorization(abort_on_fail=False)
    def channel_item(self, userid, channelid):
        channel = Channel.query.get_or_404(channelid)
        data = video_api.channel_dict(channel)
        items, total = video_api.get_local_videos(self.get_locale(), self.get_page(), channel=channelid, with_channel=False)
        data['videos'] = dict(items=items, total=total)
        return data

    @expose_ajax('/<userid>/channels/<channelid>/', methods=('PUT',))
    @check_authorization(self_auth=True)
    def channel_item_edit(self, userid, channelid):
        channel = Channel.query.get_or_404(channelid)
        if not channel.owner == g.authorized.userid:
            abort(403)
        form = ChannelForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)

        channel.title = form.title.data
        channel.description = form.description.data
        channel.cover = form.cover.data
        # XXX: This is broken!
        channel.locale = form.locale.data
        channel.category = form.category.data
        channel.save()

    @expose_ajax('/<userid>/cover_art/', cache_age=60, cache_private=True)
    @check_authorization(self_auth=True)
    def get_user_cover_art(self, userid):
        covers = UserCoverArt.query.filter_by(owner=userid)
        return cover_api.cover_art_response(covers, self.get_page())

    @expose_ajax('/<userid>/cover_art/', methods=['POST'])
    @check_authorization(self_auth=True)
    def post_user_cover_art(self, userid):
        image_data = process_image(UserCoverArt.cover)
        cover = UserCoverArt(cover=path, owner=userid)
        cover = cover.save()
        return cover_api.cover_art_dict(cover), 201
