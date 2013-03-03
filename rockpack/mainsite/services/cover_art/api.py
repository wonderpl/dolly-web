from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.services.cover_art.models import RockpackCoverArt


def cover_art_dict(instance):
    return {'cover_ref': str(instance.cover),
            'carousel_url': instance.cover.carousel,
            'background_url': instance.cover.background}


def cover_art_response(covers, paging):
    total = covers.count()
    offset, limit = paging
    items = [cover_art_dict(c) for c in covers.offset(offset).limit(limit)]
    return dict(cover_art=dict(items=items, total=total))


class CoverArtWS(WebService):

    endpoint = '/cover_art'

    @expose_ajax('/', cache_age=600)
    def rockpack_cover_art(self):
        covers = RockpackCoverArt.query.filter_by(locale=self.get_locale())
        return cover_art_response(covers, self.get_page())
