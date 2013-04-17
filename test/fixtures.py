from datetime import date
from fixture import DataSet
from fixture import SQLAlchemyFixture

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
        parent = None

    class Series:
        id = 1
        name = 'Series'
        parent = 1

    class Music:
        id = 2
        name = 'Music'
        parent = None

    class Rock:
        id = 3
        name = 'Rock'
        parent = 2


class CategoryTranslationData(DataSet):
    class TV:
        id = 0
        name = 'TV'
        locale = LocaleData.US.id
        category = CategoryData.TV.id

    class Series:
        id = 1
        name = 'Series'
        locale = LocaleData.US.id
        category = CategoryData.Series.id

    class Music:
        id = 2
        name = 'Music'
        locale = LocaleData.US.id
        category = CategoryData.Music.id

    class Rock:
        id = 3
        name = 'Rock'
        locale = LocaleData.US.id
        category = CategoryData.Rock.id


class RockpackCoverArtData(DataSet):
    class comic_cover:
        cover = 'comic.png'
        locale = LocaleData.US.id


class UserData(DataSet):
    class test_user_a:
        id = 'xtpqTpGMTti2OAyohMRPLQ'
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


class ChannelData(DataSet):
    class channel1:
        id = 'ch6JCPZAcXSjGroanQdVB8jw'
        owner = UserData.test_user_a.id
        title = 'channel #1'
        description = ''
        cover = ''
        category = 3


class ChannelLocaleMetaData(DataSet):
    class channel1_meta:
        channel = ChannelData.channel1.id
        locale = LocaleData.US.id


class VideoData(DataSet):
    class video1:
        id = 'RP000001ZQAIPJR6SDO436GDXWNPBOH6YXPLSOFZ'
        title = 'A video'
        source = 1
        source_videoid = 'xxx'


class VideoInstanceData(DataSet):
    class video_instance1:
        id = 'viw4MLuit1R5WAB4LSQDUo7Q'
        video = VideoData.video1.id
        channel = ChannelData.channel1.id
        category = 0


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
            'CategoryTranslationData': video_models.CategoryTranslation,
            'RockpackCoverArtData': RockpackCoverArt,
            'SourceData': video_models.Source,
            'UserData': User,
            'ChannelData': video_models.Channel,
            'ChannelLocaleMetaData': video_models.ChannelLocaleMeta,
            'VideoData': video_models.Video,
            'VideoInstanceData': video_models.VideoInstance,
        },
        engine=db.engine)

    data = dbfixture.data(*args)
    data.setup()
