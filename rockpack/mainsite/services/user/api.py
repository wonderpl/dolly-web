from flask import jsonify, abort, request

from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.services.video.models import (
    ChannelLocaleMeta, Video, VideoInstance, VideoLocaleMeta)
from rockpack.mainsite.services.cover_art.models import UserCoverArt
from rockpack.mainsite.services.cover_art import api as cover_api
from rockpack.mainsite.services.video import api as video_api
from rockpack.mainsite.helpers.http import cache_for
from .models import UserActivity


ACTION_COLUMN_VALUE_MAP = dict(
    view=('view_count', 1),
    star=('star_count', 1),
    unstar=('star_count', -1),
)


@commit_on_success
def _increment_video_count(instance_id, locale, column, value=1):
    instance = VideoInstance.query.filter_by(id=instance_id)
    video_id = instance.value(VideoInstance.video)
    video = Video.query.filter_by(id=video_id)
    meta = VideoLocaleMeta.query.filter_by(video=video_id, locale=locale)

    incr_count = lambda m: {getattr(m, column): getattr(m, column) + value}
    instance.update(incr_count(VideoInstance))
    video.update(incr_count(Video))
    meta.update(incr_count(VideoLocaleMeta))


class UserAPI(WebService):

    endpoint = '/'

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
            action = request.form['action']
            if action not in ACTION_COLUMN_VALUE_MAP:
                abort(400)

            instance_id = request.form['video_instance']
            if not VideoInstance.query.filter_by(id=instance_id).count():
                abort(400)

            activity = dict(user=userid, action=action,
                            object_type='video_instance', object_id=instance_id)
            if not UserActivity.query.filter_by(**activity).count():
                column, value = ACTION_COLUMN_VALUE_MAP[action]
                _increment_video_count(instance_id, self.get_locale(), column, value)
            UserActivity(**activity).save()
            return jsonify()
        else:
            # Return list of recent views?
            return jsonify([])

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
