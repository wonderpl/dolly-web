from datetime import date
from fixture import DataSet
from fixture import SQLAlchemyFixture

from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.services.cover_art.models import RockpackCoverArt
from rockpack.mainsite.services.video import models as video_models
from rockpack.mainsite.services.user.models import User


class LocaleData(DataSet):
    class UK:
        id = 'en-gb'
        name = 'UK'

    class US:
        id = 'en-us'
        name = 'US'


class SourceData(DataSet):
    class Rockpack:
        id = 0
        label = 'rockpack'
        player_template = 'r'

    class Youtube:
        id = 1
        label = 'youtube'
        player_template = 'y'


class CategoryData(DataSet):
    class TV:
        id = 0
        name = 'TV'
        locale = LocaleData.US.id
        parent = None

    class Series:
        id = 1
        name = 'Series'
        locale = LocaleData.US.id
        parent = 0

    class Music:
        id = 2
        name = 'Music'
        locale = LocaleData.US.id
        parent = None

    class Rock:
        id = 3
        name = 'Rock'
        locale = LocaleData.US.id
        parent = 2


class RockpackCoverArtData(DataSet):
    class comic_cover:
        cover = 'comic.png'
        locale = LocaleData.US.id


class UserData(DataSet):
    class test_user_a:
        username = 'test_user_1'
        password_hash = ''
        email = 'test@user.com'
        first_name = 'test'
        last_name = 'user'
        date_of_birth = date(2000, 1, 1)
        avatar = ''
        is_active = True
        refresh_token = ''
        locale = LocaleData.US.id


all_data = [v for k, v in globals().copy().iteritems() if k.endswith('Data')]

# patch for sqlalchemy and SessionMaker

from flask.ext.sqlalchemy import _SignalTrackingMapperExtension, orm
from sqlalchemy.orm.interfaces import EXT_CONTINUE


def _record(self, mapper, model, operation):
    pk = tuple(mapper.primary_key_from_instance(model))
    # Some hack just to prevent from crashing when trying to look
    # for _model_changes attribute. Happens when loading fixutres with
    # the fixture library.
    if not hasattr(orm.object_session(model), '_model_changes'):
        orm.object_session(model)._model_changes = dict()
    orm.object_session(model)._model_changes[pk] = (model, operation)
    return EXT_CONTINUE


# duck punch
_SignalTrackingMapperExtension._record = _record


def install(*args):

    dbfixture = SQLAlchemyFixture(
        env={
            'LocaleData': video_models.Locale,
            'CategoryData': video_models.Category,
            'RockpackCoverArtData': RockpackCoverArt,
            'SourceData': video_models.Source,
            'UserData': User,
        },
        engine=db.engine)

    data = dbfixture.data(*args)
    with app.test_request_context():
        data.setup()
