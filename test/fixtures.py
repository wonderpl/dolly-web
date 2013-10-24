from datetime import datetime, date
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
        id = 1
        name = 'TV'
        parent = None

    class Series:
        id = 2
        name = 'Series'
        parent = 1

    class Music:
        id = 3
        name = 'Music'
        parent = None

    class Rock:
        id = 4
        name = 'Rock'
        parent = 3


class CategoryTranslationData(DataSet):
    class TV:
        id = 1
        name = 'TV'
        locale = LocaleData.US.id
        category = CategoryData.TV.id

    class Series:
        id = 2
        name = 'Series'
        locale = LocaleData.US.id
        category = CategoryData.Series.id

    class Music:
        id = 3
        name = 'Music'
        locale = LocaleData.US.id
        category = CategoryData.Music.id

    class Rock:
        id = 4
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
        password_hash = 'sha1$WaxVi6jh$ed528a3a932fa1293b30dee6fcd2b518c78663e3'
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
        public = True
        description = ''
        cover = RockpackCoverArtData.comic_cover.cover
        category = 4
        subscriber_count = 34

    class channel2:
        id = 'ch6JCPZAfsdsGroanQdVB8jw'
        owner = UserData.test_user_a.id
        title = 'channel #2'
        description = ''
        cover = RockpackCoverArtData.comic_cover.cover
        category = 4
        subscriber_count = 7

    class channel3:
        id = 'ch6JCPZAcXSj4r34eQdVB8jw'
        owner = UserData.test_user_a.id
        title = 'channel #3'
        description = ''
        cover = RockpackCoverArtData.comic_cover.cover
        category = 4
        subscriber_count = 10

    class channel4:
        id = 'ch6JCPZAc5g4wsg4nQdVB8jw'
        owner = UserData.test_user_a.id
        title = 'channel #4'
        description = ''
        cover = RockpackCoverArtData.comic_cover.cover
        category = 4
        subscriber_count = 2

    class channel5:
        id = 'ch6JCPZlkjhlkloanQdVB8jw'
        owner = UserData.test_user_a.id
        title = 'channel #5'
        description = ''
        cover = RockpackCoverArtData.comic_cover.cover
        category = 4
        subscriber_count = 60

    class channel6:
        id = 'ch6JCPZAcXSjGrfdsa8908jw'
        owner = UserData.test_user_a.id
        title = 'channel #6'
        description = ''
        cover = RockpackCoverArtData.comic_cover.cover
        category = 2
        subscriber_count = 9


class ChannelLocaleMetaData(DataSet):
    class channel1_meta:
        channel = ChannelData.channel1.id
        locale = LocaleData.US.id
        view_count = 0
        star_count = 0

    class channel2_meta:
        channel = ChannelData.channel2.id
        locale = LocaleData.US.id
        view_count = 10
        star_count = 10

    class channel3_meta:
        channel = ChannelData.channel3.id
        locale = LocaleData.US.id
        view_count = 10
        star_count = 20

    class channel4_meta:
        channel = ChannelData.channel4.id
        locale = LocaleData.US.id
        view_count = 20
        star_count = 20

    class channel5_meta:
        channel = ChannelData.channel5.id
        locale = LocaleData.US.id
        view_count = 74
        star_count = 30

    class channel6_meta:
        channel = ChannelData.channel6.id
        locale = LocaleData.US.id
        view_count = 30
        star_count = 10

    class channel7_meta:
        channel = ChannelData.channel1.id
        locale = LocaleData.UK.id
        view_count = 35
        star_count = 10

    class channel8_meta:
        channel = ChannelData.channel2.id
        locale = LocaleData.UK.id
        view_count = 50
        star_count = 0

    class channel9_meta:
        channel = ChannelData.channel3.id
        locale = LocaleData.UK.id
        view_count = 3
        star_count = 0

    class channel10_meta:
        channel = ChannelData.channel4.id
        locale = LocaleData.UK.id
        view_count = 120
        star_count = 0

    class channel11_meta:
        channel = ChannelData.channel5.id
        locale = LocaleData.UK.id
        view_count = 74
        star_count = 1

    class channel12_meta:
        channel = ChannelData.channel6.id
        locale = LocaleData.UK.id
        view_count = 10
        star_count = 10


class VideoData(DataSet):
    class video1:
        id = 'RP000001GZVLQVP5S5M3T6VMQZKSJQW6DVUV4VHY'
        title = 'A video'
        source = 1
        source_videoid = 'lBFBbm1Nudc'
        date_published = datetime(2013, 1, 1, 0, 0, 0)

    class video2:
        id = 'RP000001BM5SNPLFSO4UKGVWVI4PKAY3S7WOTZQ4'
        title = 'Primer'
        source = 1
        source_videoid = 'xax'
        date_published = datetime(2013, 1, 1, 0, 0, 0)

    class video3:
        id = 'RP000001ZQAIPJR6SDHKJLDHJKNPBOH6YXPLSOFZ'
        title = 'Another 48hrs'
        source = 1
        source_videoid = 'xxg'
        date_published = datetime(2013, 1, 1, 0, 0, 0)

    class video4:
        id = 'RP000001DEZDWWGBIGYZ6W7T7PWYHAUV66SLRC35'
        title = 'Aliens'
        source = 1
        source_videoid = 'xqx'
        date_published = datetime(2013, 1, 1, 0, 0, 0)

    class video5:
        id = 'RP000001AVL4XQTZAZV4BG6UE4ZFHMQLPAAR7DVL'
        title = 'Predator'
        source = 1
        source_videoid = 'xwx'
        date_published = datetime(2013, 1, 1, 0, 0, 0)

    class video6:
        id = 'RP000001EWZR7BWQLFNDVZOIUIMAAIFUN5DGOSET'
        title = 'Office Space'
        source = 1
        source_videoid = 'xdx'
        date_published = datetime(2013, 1, 1, 0, 0, 0)


class VideoInstanceData(DataSet):
    class video_instance1:
        id = 'viw4MLuit1R5WAB4LSQDUo7Q'
        video = VideoData.video1.id
        channel = ChannelData.channel1.id
        category = 1

    class video_instance2:
        id = 'viw4MLuit1R5dasdasQDUo7Q'
        video = VideoData.video2.id
        channel = ChannelData.channel2.id
        category = 2

    class video_instance3:
        id = 'viw4MLuit1R5W5464SQDUo7Q'
        video = VideoData.video3.id
        channel = ChannelData.channel2.id
        category = 2

    class video_instance4:
        id = 'viw4MLu432R5WfasdfQDUo7Q'
        video = VideoData.video4.id
        channel = ChannelData.channel3.id
        category = 3

    class video_instance5:
        id = 'viw4MLuitlfdsAB4LSQDUo7Q'
        video = VideoData.video5.id
        channel = ChannelData.channel3.id
        category = 3

    class video_instance6:
        id = 'viw4MLu432R5jkldsaQDUo7Q'
        video = VideoData.video6.id
        channel = ChannelData.channel4.id
        category = 4

    class video_instance7:
        id = 'viw4MLuit1R5jkl543QDUo7Q'
        video = VideoData.video3.id
        channel = ChannelData.channel5.id
        category = 4

    class video_instance8:
        id = 'viw4MLuit1RfdsdssaQDUo7Q'
        video = VideoData.video2.id
        channel = ChannelData.channel6.id
        category = 4

    class video_instance9:
        id = 'viw4MLuit1RgfdldsaQDUo7Q'
        video = VideoData.video1.id
        channel = ChannelData.channel6.id
        category = 4


all_data = [v for k, v in globals().copy().iteritems() if k.endswith('Data')]


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
    with app.test_request_context():
        data.setup()
