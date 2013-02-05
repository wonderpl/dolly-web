from fixture import DataSet
from fixture import SQLAlchemyFixture

import json

from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.cover_art.models import RockpackCoverArt

from test import base


# TODO: move these so that they load
#  somewhere near the imported test class
class LocaleData(DataSet):
    class UK:
        id = 'en-gb'
        name = 'UK'

    class US:
        id = 'en-us'
        name = 'US'


class RockpackCoverArtData(DataSet):
    class comic_cover:
        cover = 'image.jpg'
        locale = LocaleData.UK.id


dbfixture = SQLAlchemyFixture(
        env={'LocaleData': models.Locale,
            'RockpackCoverArtData': RockpackCoverArt},
        engine=db.engine)


class CoverArtTestCase(base.FixtureTestCase):
    fixture = dbfixture
    datasets = [LocaleData, RockpackCoverArtData]

    maxDiff = None

    def test_rockpack_cover(self):
        with self.app.test_client() as client:
            r = client.get('/ws/cover_art/')
            j = json.loads(r.data)
            self.assertEquals(j['cover_art'][0]['id'], 1, 'ids should match')
            print j['cover_art'][0]['background_url']
            assert j['cover_art'][0]['background_url'].startswith(
                     '{0}/images/channel/background/'.format(self.app.config['IMAGE_CDN']))
            assert j['cover_art'][0]['carousel_url'].startswith(
                     '{0}/images/channel/carousel/'.format(self.app.config['IMAGE_CDN']))

