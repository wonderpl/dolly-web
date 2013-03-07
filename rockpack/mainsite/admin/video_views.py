from flask.ext.admin.model.typefmt import Markup
from flask.ext.admin.model.form import InlineFormAdmin
from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.cover_art import models as coverart_models


def _format_video_thumbnail(context, video, name):
    t = '<a target="_blank" href="%s"><img src="%s" width="160" height="90"/></a>'
    return Markup(t % (video.player_link, video.default_thumbnail))


def _format_video_instance_link(context, video, name):
    t = '<a href="/admin/video_locale_meta/?flt1_2={}">{}</a>'
    return Markup(t.format(video.video_rel.title, video.video_rel.title))


class VideoLocaleMetaFormAdmin(InlineFormAdmin):
    form_columns = ('id', 'category_ref', 'visible')


class Video(AdminView):
    model_name = 'video'
    model = models.Video

    column_list = ('title', 'date_updated', 'thumbnail')
    column_formatters = dict(thumbnail=_format_video_thumbnail)
    column_filters = ('source_listid', 'sources', 'date_added', 'metas')
    column_searchable_list = ('title',)
    form_columns = ('title', 'sources', 'source_videoid', 'rockpack_curated')

    inline_models = (VideoLocaleMetaFormAdmin(models.VideoLocaleMeta),)


class VideoThumbnail(AdminView):
    model_name = 'video_thumbnail'
    model = models.VideoThumbnail

    column_filters = ('video_rel',)


class VideoLocaleMeta(AdminView):
    model = models.VideoLocaleMeta
    model_name = model.__tablename__

    column_filters = ('video_rel', 'category_ref', 'locale_rel', 'visible',)


class VideoInstance(AdminView):
    model_name = 'video_instance'
    model = models.VideoInstance

    column_list = ('video_rel', 'video_channel', 'date_added', 'thumbnail')
    column_formatters = dict(thumbnail=_format_video_thumbnail, video_rel=_format_video_instance_link)
    column_filters = ('video_channel', 'video_rel')
    form_columns = ('video_channel', 'video_rel')


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


class ChannelLocaleMetaFormAdmin(InlineFormAdmin):
    form_columns = ('id', 'channel_locale', 'visible')

    def postprocess_form(self, form):
        # TODO: make category selection dynamic, based on locale
        #form.category_ref = wtf.HiddenField()
        return form


class Channel(AdminView):
    model_name = 'channel'
    model = models.Channel

    column_list = ('title', 'owner_rel', 'cover.thumbnail_large')
    column_filters = ('owner_rel', 'title', 'metas')
    column_searchable_list = ('title',)

    inline_models = (ChannelLocaleMetaFormAdmin(models.ChannelLocaleMeta),)

    edit_template = 'admin/edit_with_child_links.html'
    child_links = (('Videos', 'video_instance', 'title'),)


class RockpackCoverArt(AdminView):
    model = coverart_models.RockpackCoverArt
    model_name = coverart_models.RockpackCoverArt.__tablename__

    column_list = ('locale_rel', 'cover.thumbnail_large')
    column_filters = ('locale_rel',)

    edit_template = 'admin/cover_art.html'


class UserCoverArt(AdminView):
    model = coverart_models.UserCoverArt
    model_name = coverart_models.UserCoverArt.__tablename__

    column_list = ('owner_rel', 'cover.thumbnail_large', 'cover',)
    column_filters = ('owner_rel',)

    edit_template = 'admin/cover_art.html'


class ChannelLocaleMeta(AdminView):
    model_name = 'channel_locale_meta'
    model = models.ChannelLocaleMeta

    column_filters = ('channel_rel',)


class ExternalCategoryMap(AdminView):
    model_name = 'external_category_map'
    model = models.ExternalCategoryMap


registered = [
    Video, VideoLocaleMeta, VideoThumbnail, VideoInstance,
    Source, Category, CategoryMap, Locale, RockpackCoverArt,
    UserCoverArt, Channel, ChannelLocaleMeta, ExternalCategoryMap]


def admin_views():
    for v in registered:
        yield v(name=v.__name__,
                endpoint=v.model_name,
                category='Video',)
