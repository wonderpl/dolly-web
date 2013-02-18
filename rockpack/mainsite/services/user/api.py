from flask import g, jsonify, abort, request

from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.services.video.models import ChannelLocaleMeta
from rockpack.mainsite.services.cover_art.models import UserCoverArt
from rockpack.mainsite.services.cover_art import api as cover_api
from rockpack.mainsite.services.video import api as video_api
from rockpack.mainsite.helpers.http import cache_for


class UserAPI(WebService):

    endpoint = '/'

    # TODO: hack for recent videos. do this properly
    @expose('/<string:userid>/subscriptions/recent_videos/')
    @cache_for(seconds=60, private=True)
    def recent_videos(self, userid):
        data, total = video_api.get_local_videos(self.get_locale(), self.get_page(), date_order=True, **request.args)
        response = jsonify({'videos': {'items': data, 'total': total}})
        return response

    @expose('/<string:userid>/channels/<string:channelid>/', methods=('GET',))
    @cache_for(seconds=60)
    def channel_item(self, userid, channelid):
        meta = g.session.query(ChannelLocaleMeta).filter_by(
            channel=channelid).first()
        if not meta:
            abort(404)
        data = video_api.channel_dict(meta.channel_rel)
        items, total = video_api.get_local_videos(self.get_locale(), self.get_page(), channel=channelid, with_channel=False)
        data['videos'] = dict(items=items, total=total)
        response = jsonify(data)
        return response

    @expose('/<string:userid>/cover_art/', methods=('GET', 'POST',))
    @cache_for(seconds=60)
    def user_cover_art(self, userid):
        if request.method == 'POST':
            uca = UserCoverArt(cover=request.files['file'], owner=userid)
            g.session.add(uca)
            g.session.commit()
            response = jsonify({'cover_art': [cover_api.cover_art_dict(uca)]})
            response.status_code = 201
            return response

        covers = g.session.query(UserCoverArt).filter(
                UserCoverArt.owner == userid)

        response = jsonify({'cover_art': [cover_api.cover_art_dict(c) for c in covers]})
        return response
