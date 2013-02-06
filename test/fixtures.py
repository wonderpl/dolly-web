from fixture import DataSet
from fixture import SQLAlchemyFixture

from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.services.cover_art.models import RockpackCoverArt
from rockpack.mainsite.services.video import models as video_models
from rockpack.mainsite.auth.models import User


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
        locale = LocaleData.US.id


class UserData(DataSet):
    class test_user_a:
        username = 'test_user_1'
        email = 'test@user.com'
        first_name = 'test'
        last_name = 'user'
        avatar = 'avatar.jpg'


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
            env={'LocaleData': video_models.Locale,
                'RockpackCoverArtData': RockpackCoverArt,
                'UserData': User},
            engine=db.engine)

    data = dbfixture.data(*args)
    data.setup()
