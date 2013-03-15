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
    t = u'<a href="/admin/video_locale_meta/?flt1_2={}">{}</a>'
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
    form_overrides = dict(video_rel=wtf.TextField,
            view_count=wtf.TextField,
            star_count=wtf.TextField,
            )
    from_args = dict(
            view_count=dict(validators=[wtf.InputRequired()]),
            star_count=dict(validators=[wtf.InputRequired()]),
            )

    column_filters = ('video_rel', 'category_ref', 'locale_rel', 'visible',)


class VideoInstance(AdminView):
    model_name = 'video_instance'
    model = models.VideoInstance

    form_overrides = dict(video_rel=wtf.TextField)

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

    def scaffold_filters(self, name):
        filters = super(Category, self).scaffold_filters(name)
        # Allow filtering by "parent is NULL":
        if name == 'parent':
            filters[0].clean = lambda v: None if v == '' else v
        return filters


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


def _format_channel_metas(context, channel, name):
    text = ''
    for clm in models.ChannelLocaleMeta.query.filter_by(channel=channel.id):
        cat = models.Category.query.get(clm.category)
        text+= '<p>' + clm.locale + '</br>{}/{}'.format(cat.parent_category.name, cat.name) + '</p>'
    return Markup(text)


def _format_channel_video_count(context, channel, name):
    count = models.VideoInstance.query.filter(models.VideoInstance.channel==channel.id).count()
    return Markup('{}'.format(count))



class Channel(AdminView):
    model_name = 'channel'
    model = models.Channel

    form_overrides = dict(owner_rel=wtf.TextField)
    column_auto_select_related = True
    column_display_all_relations = True

    column_list = ('title', 'owner_rel', 'public', 'cover.thumbnail_large', 'metas', 'video_count', 'date_added')
    column_filters = ('owner', 'title', 'public', models.Channel.metas)
    column_searchable_list = ('title',)
    column_formatters = dict(metas=_format_channel_metas,
            video_count=_format_channel_video_count)

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

    form_overrides = dict(owner_rel=wtf.TextField)
    column_list = ('owner_rel', 'cover.thumbnail_large', 'cover',)
    column_filters = ('owner_rel',)

    edit_template = 'admin/cover_art.html'


class ChannelLocaleMeta(AdminView):
    model_name = 'channel_locale_meta'
    model = models.ChannelLocaleMeta

    form_overrides = dict(channel_rel=wtf.TextField,
            view_count=wtf.TextField,
            star_count=wtf.TextField,
            )

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
