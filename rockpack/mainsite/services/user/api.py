from sqlalchemy import desc
from flask import jsonify, abort, request
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.services.video.models import (
    Channel, ChannelLocaleMeta, Video, VideoInstance, VideoLocaleMeta)
from rockpack.mainsite.services.cover_art.models import UserCoverArt
from rockpack.mainsite.services.cover_art import api as cover_api
from rockpack.mainsite.services.video import api as video_api
from rockpack.mainsite.helpers.http import cache_for
from .models import User, UserActivity


FAVOURITE_CHANNEL_TITLE = 'favourites'

ACTION_COLUMN_VALUE_MAP = dict(
    view=('view_count', 1),
    star=('star_count', 1),
    unstar=('star_count', -1),
)


@commit_on_success
def save_video_activity(user, action, instance_id, locale):
    try:
        column, value = ACTION_COLUMN_VALUE_MAP[action]
    except KeyError:
        abort(400)

    instance = VideoInstance.query.filter_by(id=instance_id)
    video_id = instance.value(VideoInstance.video)
    if not video_id:
        abort(400)

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
            owner=user, title=FAVOURITE_CHANNEL_TITLE).first()
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


class UserAPI(WebService):

    endpoint = '/'

    @expose('/<string:userid>/')
    @cache_for(seconds=60, private=True)
    def user_info(self, userid):
        user = User.query.get_or_404(userid)
        # TODO: we'll need to check if authenticated user is owner and include private channels
        channels = [video_api.channel_dict(c, with_owner=False) for c in user.channels]
        return jsonify(
            name=user.username,
            display_name=user.display_name,
            avatar_thumbnail_url=user.avatar.thumbnail_small,
            channels=channels,
        )

    # TODO: hack for recent videos. do this properly
    @expose('/<string:userid>/subscriptions/recent_videos/')
    @cache_for(seconds=60, private=True)
    def recent_videos(self, userid):
        data, total = video_api.get_local_videos(self.get_locale(), self.get_page(), date_order=True, **request.args)
        response = jsonify({'videos': {'items': data, 'total': total}})
        return response

    @expose('/<string:userid>/activity/', methods=('GET', 'POST'))
    @cache_for(seconds=60, private=True)
    def activity(self, userid):
        if request.method == 'POST':
            save_video_activity(userid,
                                request.form['action'],
                                request.form['video_instance'],
                                self.get_locale())
            return jsonify()
        else:
            return jsonify(
                recently_viewed=action_object_list(userid, 'view', self.max_page_size),
                recently_starred=action_object_list(userid, 'star', self.max_page_size),
                subscribed=[],
            )

    @expose('/<string:userid>/channels/<string:channelid>/', methods=('GET',))
    @cache_for(seconds=60)
    def channel_item(self, userid, channelid):
        meta = ChannelLocaleMeta.query.filter_by(channel=channelid).first_or_404()
        data = video_api.channel_dict(meta.channel_rel)
        items, total = video_api.get_local_videos(self.get_locale(), self.get_page(), channel=channelid, with_channel=False)
        data['videos'] = dict(items=items, total=total)
        response = jsonify(data)
        return response

    @expose('/<string:userid>/cover_art/', methods=('GET', 'POST',))
    @cache_for(seconds=60)
    def user_cover_art(self, userid):
        if request.method == 'POST':
            cover = UserCoverArt(cover=request.files['file'], owner=userid)
            cover = cover.save()
            response = jsonify(cover_api.cover_art_dict(cover))
            response.status_code = 201
            return response
        else:
            covers = UserCoverArt.query.filter_by(owner=userid)
            return cover_api.cover_art_response(covers, self.get_page())
