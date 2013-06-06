from flask import request
from sqlalchemy import desc
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.services.cover_art.models import RockpackCoverArt


def cover_art_dict(instance, own=False):
    data = dict(
        id=str(instance.id),
        cover_ref=str(instance.cover),
        thumbnail_url=instance.cover.url,
    )
    if getattr(instance, 'category', None):
        data['category'] = str(instance.category)
    if own:
        data['resource_url'] = instance.get_resource_url(own)
    return data


def cover_art_response(covers, paging, own=False):
    total = covers.count()
    offset, limit = paging
    items = [dict(position=position, **cover_art_dict(cover_art, own))
             for position, cover_art in enumerate(covers.offset(offset).limit(limit), offset)]
    return dict(cover_art=dict(items=items, total=total))


class CoverArtWS(WebService):

    endpoint = '/cover_art'

    @expose_ajax('/', cache_age=600)
    def rockpack_cover_art(self):
        # Get global and local cover art
        query = RockpackCoverArt.query.\
            filter(RockpackCoverArt.locale.in_(('', self.get_locale()))).\
            filter(RockpackCoverArt.priority != -1).\
            order_by(desc('priority'))
        if request.args.get('category'):
            query = query.filter_by(category=request.args.get('category'))
        return cover_art_response(query, self.get_page())
