from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.services.video import models


class Video(AdminView):
    model_name = 'video'
    model = models.Video

    create_template = 'admin/video/create.html'

    inline_models = (models.VideoThumbnail, )


class VideoThumbnail(AdminView):
    model_name = 'video_thumbnail'
    model = models.VideoThumbnail


class VideoInstance(AdminView):
    model_name = 'video_instance'
    model = models.VideoInstance


class Source(AdminView):
    model_name = 'source'
    model = models.Source


class Category(AdminView):
    model_name = 'category'
    model = models.Category


class Locale(AdminView):
    model_name = 'locale'
    model = models.Locale


class Channel(AdminView):
    model_name = 'channel'
    model = models.Channel


class ExternalCategoryMap(AdminView):
    model_name = 'external_category_map'
    model = models.ExternalCategoryMap


registered = [Video, VideoThumbnail, VideoInstance,
        Source, Category, Locale, Channel, ExternalCategoryMap]


def admin_views():
    for v in registered:
        yield v(name=v.__name__,
                endpoint=v.model_name,
                category='Video',)
