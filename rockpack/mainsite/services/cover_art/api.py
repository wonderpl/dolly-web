from flask import g, jsonify

from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.services.cover_art import models
from rockpack.mainsite.helpers.http import cache_for


def cover_art_dict(instance):
    return {'id': instance.id,
            'carousel_url': instance.cover.carousel,
            'background_url': instance.cover.background}


class CoverArtAPI(WebService):

    endpoint = '/cover_art'

    @expose('/', methods=('GET',))
    @cache_for(seconds=300)
    def rockpack_cover_art(self):
        covers = g.session.query(models.RockpackCoverArt).filter(
                models.RockpackCoverArt.locale == self.get_locale())

        response = jsonify({'cover_art': [cover_art_dict(c) for c in covers]})
        return response
