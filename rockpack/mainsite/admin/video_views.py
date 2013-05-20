from flask.ext import wtf
from flask.ext.admin.model.typefmt import Markup
from flask.ext.admin.model.form import InlineFormAdmin
from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.cover_art import models as coverart_models


def _format_video_thumbnail(context, video, name):
    t = u'<a target="_blank" href="%s"><img src="%s" width="160" height="90"/></a>'
    return Markup(t % (video.player_link, video.default_thumbnail))


def _format_video_instance_link(context, video, name):
    t = u'<a href="/admin/video/?flt1_0={}">{}</a>'
    return Markup(t.format(video.video, video.video_rel.title))


class VideoInstanceLocaleMetaFormAdmin(InlineFormAdmin):
    form_columns = ('id', 'locale_rel')


class Video(AdminView):
    model_name = 'video'
    model = models.Video

    column_list = ('title', 'date_updated', 'thumbnail', 'visible')
    column_formatters = dict(thumbnail=_format_video_thumbnail)
    column_filters = ('id', 'source_listid', 'sources', 'date_added', 'visible')
    column_searchable_list = ('title',)
    form_columns = ('title', 'sources', 'source_videoid', 'rockpack_curated', 'visible')


class VideoThumbnail(AdminView):
    model_name = 'video_thumbnail'
    model = models.VideoThumbnail

    column_filters = ('video_rel',)


class VideoInstanceLocaleMeta(AdminView):
    model = models.VideoInstanceLocaleMeta
    model_name = model.__tablename__
    form_overrides = dict(
        video_instance_rel=wtf.TextField,
        view_count=wtf.TextField,
        star_count=wtf.TextField,
    )
    from_args = dict(
        view_count=dict(validators=[wtf.InputRequired()]),
        star_count=dict(validators=[wtf.InputRequired()]),
    )

    column_filters = ('video_instance_rel', 'locale_rel',)


class VideoInstance(AdminView):
    model_name = 'video_instance'
    model = models.VideoInstance

    form_overrides = dict(video_rel=wtf.TextField)

    column_list = ('video_rel', 'video_channel', 'date_added', 'category_rel', 'thumbnail')
    column_formatters = dict(thumbnail=_format_video_thumbnail, video_rel=_format_video_instance_link)
    column_filters = ('channel', 'video_rel', 'metas', 'category_rel')
    form_columns = ('video_channel', 'video_rel', 'position', 'date_added')

    inline_models = (VideoInstanceLocaleMetaFormAdmin(models.VideoInstanceLocaleMeta),)


class Source(AdminView):
    model_name = 'source'
    model = models.Source


class ChildCategoryFormAdmin(InlineFormAdmin):
    form_columns = ('name', 'id')


class CategoryTranslationFormAdmin(InlineFormAdmin):
    pass


class Category(AdminView):
    model_name = 'category'
    model = models.Category

    column_list = ('name', 'parent_category', 'parent')
    column_filters = ('parent', 'name')
    column_searchable_list = ('name',)
    form_columns = ('name', )

    inline_models = (
        ChildCategoryFormAdmin(models.Category),
        CategoryTranslationFormAdmin(models.CategoryTranslation))

    def scaffold_filters(self, name):
        filters = super(Category, self).scaffold_filters(name)
        # Allow filtering by "parent is NULL":
        if name == 'parent':
            filters[0].clean = lambda v: None if v == '' else v
        return filters


class CategoryTranslation(AdminView):
    model_name = models.CategoryTranslation.__tablename__
    model = models.CategoryTranslation


class Locale(AdminView):
    model_name = 'locale'
    model = models.Locale

    column_list = ('id', 'name')
    form_columns = ('id', 'name')


class ChannelLocaleMetaFormAdmin(InlineFormAdmin):
    form_columns = ('id', 'channel_locale', 'visible')


def _format_channel_video_count(context, channel, name):
    count = models.VideoInstance.query.filter(models.VideoInstance.channel == channel.id).count()
    return Markup('{}'.format(count))


class Channel(AdminView):
    model_name = 'channel'
    model = models.Channel

    form_columns = ('title', 'description', 'ecommerce_url', 'cover', 'cover_aoi',
                    'owner_rel', 'category_rel',
                    'public', 'verified', 'deleted', 'editorial_boost', 'favourite')
    form_overrides = dict(owner_rel=wtf.TextField)
    form_args = dict(
        ecommerce_url=dict(validators=[wtf.Optional()]),
        description=dict(validators=[wtf.Length(max=200)]),
    )
    column_auto_select_related = True
    column_display_all_relations = True

    column_list = ('title', 'owner_rel', 'public', 'cover.url', 'category_rel', 'video_count', 'date_added')
    column_filters = ('owner', 'title', 'public', 'category_rel', 'description', 'owner_rel', 'deleted')
    column_searchable_list = ('title',)
    column_formatters = dict(video_count=_format_channel_video_count)

    inline_models = (ChannelLocaleMetaFormAdmin(models.ChannelLocaleMeta),)

    edit_template = 'admin/edit_with_child_links.html'
    child_links = (('Videos', 'video_instance', None),)


class RockpackCoverArt(AdminView):
    model = coverart_models.RockpackCoverArt
    model_name = coverart_models.RockpackCoverArt.__tablename__

    column_list = ('locale_rel', 'cover.url', 'category_rel')
    column_filters = ('locale_rel', 'category_rel')
    form_columns = ('locale_rel', 'category_rel', 'cover', 'cover_aoi', 'priority', 'attribution')

    edit_template = 'admin/cover_art_edit.html'
    create_template = 'admin/cover_art_create.html'


class UserCoverArt(AdminView):
    model = coverart_models.UserCoverArt
    model_name = coverart_models.UserCoverArt.__tablename__

    form_overrides = dict(owner_rel=wtf.TextField)
    column_list = ('owner_rel', 'cover.url')
    column_filters = ('owner_rel',)

    edit_template = 'admin/cover_art_edit.html'


class ChannelLocaleMeta(AdminView):
    model_name = 'channel_locale_meta'
    model = models.ChannelLocaleMeta

    form_overrides = dict(
        channel_rel=wtf.TextField,
        view_count=wtf.TextField,
        star_count=wtf.TextField,
    )

    column_filters = ('channel_rel', 'channel_locale')


class ContentReport(AdminView):
    model_name = 'content_report'
    model = models.ContentReport

    column_filters = ('date_created', 'reviewed', 'object_type')


class ExternalCategoryMap(AdminView):
    model_name = 'external_category_map'
    model = models.ExternalCategoryMap


registered = [
    Video, VideoInstanceLocaleMeta, VideoThumbnail, VideoInstance,
    Source, Category, CategoryTranslation, Locale, RockpackCoverArt,
    UserCoverArt, Channel, ChannelLocaleMeta, ContentReport, ExternalCategoryMap]


def admin_views():
    for v in registered:
        yield v(name=v.__name__,
                endpoint=v.model_name,
                category='Video',)
