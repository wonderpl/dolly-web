from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.services.video import models


class Video(AdminView):
    model_name = 'video'
    model = models.Video

    column_list = ['title', 'date_added', 'date_updated', 'duration', 'star_count', 'rockpack_curated', 'sources']
    column_searchable_list = ('title',)
    column_filters = ('sources', )

    create_template = 'admin/video/create.html'
    list_template = 'admin/video/list.html'

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


class Source(AdminView):
    model_name = 'source'
    model = models.Source


class Category(AdminView):
    model_name = 'category'
    model = models.Category


class CategoryMap(AdminView):
    model_name = models.CategoryMap.__tablename__
    model = models.CategoryMap


class Locale(AdminView):
    model_name = 'locale'
    model = models.Locale

    column_display_pk = True


class Channel(AdminView):
    model_name = 'channel'
    model = models.Channel


class ChannelLocaleMeta(AdminView):
    model_name = 'channel_locale_meta'
    model = models.ChannelLocaleMeta


class ExternalCategoryMap(AdminView):
    model_name = 'external_category_map'
    model = models.ExternalCategoryMap


registered = [Video, VideoLocaleMeta, VideoThumbnail, VideoInstance,
        Source, Category, CategoryMap, Locale,
        Channel, ChannelLocaleMeta, ExternalCategoryMap]


def admin_views():
    for v in registered:
        yield v(name=v.__name__,
                endpoint=v.model_name,
                category='Video',)
