from datetime import datetime
import wtforms as wtf
from flask import request
from flask.ext.admin.form import BaseForm, DateTimePickerWidget, RenderTemplateWidget
from flask.ext.admin.model.fields import AjaxSelectField
from flask.ext.admin.model.typefmt import Markup
from flask.ext.admin.model.form import InlineFormAdmin
from rockpack.mainsite import app
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.cover_art import models as coverart_models
from rockpack.mainsite.core.es import use_elasticsearch, api as es_api
from .base import AdminModelView


def _format_video_thumbnail(view, context, video, name):
    t = u'<a target="_blank" href="%s"><img src="%s" width="160" height="90"/></a>'
    return Markup(t % (video.player_link, video.default_thumbnail))


def _format_video_instance_link(view, context, video, name):
    t = u'<a href="/admin/video/?flt1_0={}">{}</a>'
    if video.video_rel:
        return Markup(t.format(video.video, video.video_rel.title))
    else:
        return ''


class VideoInstanceLocaleMetaFormAdmin(InlineFormAdmin):
    form_columns = ('id', 'locale_rel')


class VideoView(AdminModelView):
    model = models.Video

    column_list = ('title', 'date_updated', 'thumbnail', 'visible')
    column_formatters = dict(thumbnail=_format_video_thumbnail)
    column_filters = ('id', 'source_listid', 'sources', 'date_added', 'visible')
    column_searchable_list = ('title',)
    form_excluded_columns = ('date_updated', 'instances', 'restrictions')
    inline_models = (models.VideoThumbnail,)

    def after_model_change(self, form, model, is_created):
        if use_elasticsearch():
            instance_ids = [x[0] for x in models.VideoInstance.query.filter_by(video=model.id).values('id')]
            # Force video instance updates when a video
            # is changed in the admin
            async = app.config.get('ASYNC_ES_VIDEO_UPDATES', False)
            es_api.es_update_channel_videos(extant=instance_ids, async=async)


class VideoThumbnailView(AdminModelView):
    inline_model = True
    model = models.VideoThumbnail

    column_filters = ('video_rel',)


class VideoInstanceLocaleMetaView(AdminModelView):
    inline_model = True
    model = models.VideoInstanceLocaleMeta

    column_filters = ('video_instance_rel', 'locale_rel',)
    form_ajax_refs = dict(
        video_instance_rel={'fields': (models.VideoInstance.id,)},
    )


class VideoInstanceView(AdminModelView):
    model = models.VideoInstance

    column_list = ('video_rel', 'video_channel', 'date_added', 'category_rel', 'thumbnail')
    column_formatters = dict(thumbnail=_format_video_thumbnail, video_rel=_format_video_instance_link)
    column_filters = ('channel', 'video_rel', 'metas', 'category_rel')
    form_excluded_columns = ('metas', 'videoinstancecomments')
    form_ajax_refs = dict(
        video_rel={'fields': (models.Video.title,)},
        video_channel={'fields': (models.Channel.title,)},
    )
    #inline_models = (VideoInstanceLocaleMetaFormAdmin(models.VideoInstanceLocaleMeta),)

    def after_model_change(self, form, model, is_created):
        if use_elasticsearch():
            es_video = es_api.ESVideo.inserter()
            es_video.insert(model.id, model)


class SourceView(AdminModelView):
    model = models.Source


class ChildCategoryFormAdmin(InlineFormAdmin):
    form_columns = ('name', 'id')


class CategoryTranslationFormAdmin(InlineFormAdmin):
    pass


class CategoryView(AdminModelView):
    model = models.Category

    column_list = ('name', 'parent_category', 'parent')
    column_filters = ('parent', 'name')
    column_searchable_list = ('name',)
    form_columns = ('name', 'colour')
    form_args = dict(colour={'widget': RenderTemplateWidget('admin/colour_field.html')})

    edit_template = 'admin/category_edit.html'

    inline_models = (
        ChildCategoryFormAdmin(models.Category),
        CategoryTranslationFormAdmin(models.CategoryTranslation))

    def scaffold_filters(self, name):
        filters = super(CategoryView, self).scaffold_filters(name)
        # Allow filtering by "parent is NULL":
        if name == 'parent':
            filters[0].clean = lambda v: None if v == '' else v
        return filters


class CategoryTranslationView(AdminModelView):
    model = models.CategoryTranslation

    column_searchable_list = ('name',)
    column_filters = ('locale', 'name', 'category_rel')


class LocaleView(AdminModelView):
    model = models.Locale

    column_list = ('id', 'name')
    form_columns = ('id', 'name')


class ChannelLocaleMetaFormAdmin(InlineFormAdmin):
    form_columns = ('id', 'channel_locale', 'visible')


def _format_channel_video_count(view, context, channel, name):
    count = models.VideoInstance.query.filter(models.VideoInstance.channel == channel.id).count()
    return Markup('{}'.format(count))


class ChannelView(AdminModelView):
    model = models.Channel

    column_auto_select_related = True
    column_display_all_relations = True
    column_list = ('title', 'owner_rel', 'public', 'cover.url', 'category_rel', 'video_count', 'date_added', 'editorial_boost', 'subscriber_count')
    column_filters = ('owner', 'title', 'public', 'category_rel', 'description', 'owner_rel', 'deleted', 'date_added', 'editorial_boost', 'subscriber_count')
    column_searchable_list = ('title',)
    column_formatters = dict(video_count=_format_channel_video_count)

    form_excluded_columns = ('video_instances', 'channel_promotion')
    form_ajax_refs = dict(
        owner_rel={'fields': (models.User.username,)},
    )
    form_args = dict(
        ecommerce_url=dict(validators=[wtf.validators.Optional()]),
        description=dict(validators=[wtf.validators.Optional(), wtf.validators.Length(max=200)]),
    )

    inline_models = (ChannelLocaleMetaFormAdmin(models.ChannelLocaleMeta),)

    edit_template = 'admin/edit_with_child_links.html'
    child_links = (('Videos', 'video_instance', None),)


def _format_promo_state(view, context, channel_promo, name):
    now = datetime.utcnow()
    if now < channel_promo.date_start:
        state = '<div style="background-color:#FFBB33; text-align: center; border: solid 1px #FF8800; color: #FFFFFF">WAITING</div>'
    elif channel_promo.date_end < now:
        state = '<div style="background-color:#FF4444; text-align: center; border: solid 1px #CC0000; color: #FFFFFF">ENDED</div>'
    else:
        state = '<div style="background-color:#99CC00; text-align: center; border: solid 1px #669900; color: #FFFFFF">ACTIVE</div>'
    return Markup(state)


def _format_category_names(view, context, channel_promo, name):
    if channel_promo.category == 0:
        return 'All'
    return models.Category.query.get(channel_promo.category)


def _format_channel_from(view, context, channel_promo, name):
    return channel_promo.channel_rel.category_rel


def category_list():
    cats = {'0': 'All'}
    for c in models.CategoryTranslation.query.filter(models.CategoryTranslation.priority >= 0).order_by('category'):
        if cats.get(c.category) and not c.locale == 'en-gb':
            continue

        s = ''
        if c.category_rel.parent:
            s = '{} - '.format(c.category_rel.parent_category.name)
        cats[c.category] = s + c.name

    return cats.items()


class ChannelPromotionForm(BaseForm):
    channel_rel = AjaxSelectField(None)
    category = wtf.SelectField('Category')
    locale = wtf.SelectField('Locale', validators=[wtf.validators.Required()])
    position = wtf.IntegerField(validators=[wtf.validators.Required()])
    date_start = wtf.DateTimeField(validators=[wtf.validators.Required()], widget=DateTimePickerWidget())
    date_end = wtf.DateTimeField(validators=[wtf.validators.Required()], widget=DateTimePickerWidget())

    def __init__(self, *args, **kwargs):
        super(ChannelPromotionForm, self).__init__(*args, **kwargs)
        self.channel_rel.loader = ChannelPromotionView()._form_ajax_refs['channel_rel']
        self.category.choices = category_list()
        self.locale.choices = [(l.id, l.name) for l in models.Locale.query.all()]

    def validate(self):

        # stupid hack for wtform's retarded handling of zero values
        if int(self.category.data):
            self.category.data = int(self.category.data)

        if not super(ChannelPromotionForm, self).validate():
            return

        # Handle coercion here
        self.category.data = int(self.category.data)

        if self.date_start.data > self.date_end.data:
            self.date_end.errors = ['End date must be after end date']
            return

        promos = models.ChannelPromotion.query.filter(
            models.ChannelPromotion.date_end > self.date_start.data,
            models.ChannelPromotion.date_start < self.date_end.data,
            models.ChannelPromotion.date_end > datetime.utcnow(),
            models.ChannelPromotion.category == self.category.data,
            models.ChannelPromotion.locale == self.locale.data)

        check_dupe = promos.filter(models.ChannelPromotion.channel == self.channel_rel.data.id)
        if request.args.get('id'):
            check_dupe = check_dupe.filter(models.ChannelPromotion.id != int(request.args.get('id')))
        if check_dupe.count():
            self.channel_rel.errors = ['Channel is already promoted in this category']
            return

        if request.args.get('id'):
            promo = models.ChannelPromotion.query.get(int(request.args.get('id')))
            if promo.channel != self.channel_rel.data.id:
                self.channel_rel.errors = ['Channel cannot be changed once set']
                return

            promos = promos.filter(
                models.ChannelPromotion.id != request.args.get('id'))

        if int(self.position.data) > 8:
            self.position.errors = ['Only a maximum of 8 position per category can be set']
            return

        promos = promos.filter(models.ChannelPromotion.position == self.position.data)

        if promos.count():
            self.position.errors = ['Conflicts with promotion "{}"'.format(','.join([_.channel_rel.title for _ in promos.all()]))]
            return

        return True


class ChannelPromotionView(AdminModelView):
    model = models.ChannelPromotion

    form = ChannelPromotionForm
    form_ajax_refs = dict(
        channel_rel={'fields': (models.Channel.title,)},
    )

    column_formatters = dict(channel_origin=_format_channel_from, promo_state=_format_promo_state, appearing_in=_format_category_names)
    column_list = ('channel_rel', 'channel_origin', 'locale_rel', 'appearing_in', 'promo_state', 'position', 'date_start', 'date_end', 'date_added', 'date_updated')
    column_labels = dict(channel_rel='Channel', locale_rel='Target Locale', appearing_in='Target Category')
    column_filters = ('channel_rel', 'category_rel', 'locale_rel', 'position', 'date_added', 'date_updated', 'date_start', 'date_end')


class RockpackCoverArtView(AdminModelView):
    model = coverart_models.RockpackCoverArt

    column_list = ('locale_rel', 'cover.url', 'category_rel')
    column_filters = ('locale_rel', 'category_rel')
    form_excluded_columns = ('date_created',)

    edit_template = 'admin/cover_art_edit.html'
    create_template = 'admin/cover_art_create.html'


class ChannelLocaleMetaView(AdminModelView):
    inline_model = True
    model = models.ChannelLocaleMeta

    column_filters = ('channel_rel', 'channel_locale')


class ContentReportView(AdminModelView):
    model = models.ContentReport

    column_filters = ('date_created', 'reviewed', 'object_type')


class ExternalCategoryMapView(AdminModelView):
    model = models.ExternalCategoryMap


class MoodView(AdminModelView):
    model = models.Mood
