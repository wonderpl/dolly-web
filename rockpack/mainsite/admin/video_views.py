from flask.ext.admin.model.typefmt import Markup
from flask.ext.admin.model.form import InlineFormAdmin
from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.services.video import models


def _format_video_thumbnail(context, video, name):
    t = '<a target="_blank" href="%s"><img src="%s" width="160" height="90"/></a>'
    return Markup(t % (video.player_link, video.default_thumbnail))


class Video(AdminView):
    model_name = 'video'
    model = models.Video

    column_list = ('title', 'date_updated', 'thumbnail')
    column_formatters = dict(thumbnail=_format_video_thumbnail)
    column_filters = ('sources', 'date_added')
    column_searchable_list = ('title',)
    form_columns = ('title', 'sources', 'source_videoid', 'rockpack_curated')

    inline_models = (models.VideoThumbnail, )


class VideoThumbnail(AdminView):
    model_name = 'video_thumbnail'
    model = models.VideoThumbnail


class VideoLocaleMeta(AdminView):
    model = models.VideoLocaleMeta
    model_name = model.__tablename__


class VideoInstance(AdminView):
    model_name = 'video_instance'
    model = models.VideoInstance

    column_list = ('video_rel', 'video_channel', 'date_added', 'thumbnail')
    column_formatters = dict(thumbnail=_format_video_thumbnail)
    column_filters = ('video_channel',)


class Source(AdminView):
    model_name = 'source'
    model = models.Source


class ChildCategoryFormAdmin(InlineFormAdmin):
    form_columns = ('name', 'priority', 'id')


class Category(AdminView):
    model_name = 'category'
    model = models.Category

    column_list = ('name', 'parent', 'locale')
    column_filters = ('locale', 'parent')
    column_searchable_list = ('name',)
    form_columns = ('name', 'priority', 'locales')

    inline_models = (ChildCategoryFormAdmin(models.Category),)


class CategoryMap(AdminView):
    model_name = models.CategoryMap.__tablename__
    model = models.CategoryMap

    column_list = ('category_here.locale', 'category_here',
                   'category_there.locale', 'category_there')


class Locale(AdminView):
    model_name = 'locale'
    model = models.Locale

    column_list = ('id', 'name')
    form_columns = ('id', 'name')


class Channel(AdminView):
    model_name = 'channel'
    model = models.Channel

    column_list = ('title', 'owner_rel', 'cover.thumbnail_large')


class ChannelLocaleMeta(AdminView):
    model_name = 'channel_locale_meta'
    model = models.ChannelLocaleMeta


class ExternalCategoryMap(AdminView):
    model_name = 'external_category_map'
    model = models.ExternalCategoryMap


registered = [
    Video, VideoLocaleMeta, VideoThumbnail, VideoInstance,
    Source, Category, CategoryMap, Locale,
    Channel, ChannelLocaleMeta, ExternalCategoryMap]


def admin_views():
    for v in registered:
        yield v(name=v.__name__,
                endpoint=v.model_name,
                category='Video',)
