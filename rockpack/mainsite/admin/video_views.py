from datetime import datetime
from flask import request
from flask.ext import wtf
from flask.ext.admin.form import DateTimePickerWidget
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
    if video.video_rel:
        return Markup(t.format(video.video, video.video_rel.title))
    else:
        return ''


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

    column_searchable_list = ('name',)
    column_filters = ('locale', 'name', 'category_rel')


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
                    'owner_rel', 'category_rel', 'public', 'verified', 'deleted',
                    'editorial_boost', 'subscriber_count')
    form_overrides = dict(owner_rel=wtf.TextField)
    form_args = dict(
        ecommerce_url=dict(validators=[wtf.Optional()]),
        description=dict(validators=[wtf.Length(max=200)]),
    )
    column_auto_select_related = True
    column_display_all_relations = True

    column_list = ('title', 'owner_rel', 'public', 'cover.url', 'category_rel', 'video_count', 'date_added', 'editorial_boost', 'subscriber_count')
    column_filters = ('owner', 'title', 'public', 'category_rel', 'description', 'owner_rel', 'deleted', 'date_added', 'editorial_boost', 'subscriber_count')
    column_searchable_list = ('title',)
    column_formatters = dict(video_count=_format_channel_video_count)

    inline_models = (ChannelLocaleMetaFormAdmin(models.ChannelLocaleMeta),)

    edit_template = 'admin/edit_with_child_links.html'
    child_links = (('Videos', 'video_instance', None),)


def _format_promo_state(context, channel_promo, name):
    now = datetime.utcnow()
    if now < channel_promo.date_start:
        state = '<div style="background-color:#FFBB33; text-align: center; border: solid 1px #FF8800; color: #FFFFFF">WAITING</div>'
    elif channel_promo.date_end < now:
        state = '<div style="background-color:#FF4444; text-align: center; border: solid 1px #CC0000; color: #FFFFFF">ENDED</div>'
    else:
        state = '<div style="background-color:#99CC00; text-align: center; border: solid 1px #669900; color: #FFFFFF">ACTIVE</div>'
    return Markup(state)


def _format_category_names(context, channel_promo, name):
    if channel_promo.category == 0:
        return 'All'
    return models.Category.query.get(channel_promo.category)


def _format_channel_from(context, channel_promo, name):
    return channel_promo.channel_rel.category_rel


def category_list():
    cats = {'0': 'All'}
    for c in models.CategoryTranslation.query.filter(models.CategoryTranslation.priority>=0).order_by('category'):
        if cats.get(c.category) and not c.locale == 'en-gb':
            continue

        s = ''
        if c.category_rel.parent:
            s = '{} - '.format(c.category_rel.parent_category.name)
        cats[c.category] = s + c.name

    return cats.items()


class ChannelPromotionForm(wtf.Form):
    channel = wtf.TextField()
    category = wtf.SelectField('Category')
    locale = wtf.SelectField('Locale', validators=[wtf.Required()])
    position = wtf.IntegerField(validators=[wtf.Required()])
    date_start = wtf.DateTimeField(validators=[wtf.Required()], widget=DateTimePickerWidget())
    date_end = wtf.DateTimeField(validators=[wtf.Required()], widget=DateTimePickerWidget())

    def __init__(self, *args, **kwargs):
        super(ChannelPromotionForm, self).__init__(*args, **kwargs)
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

        check_dupe = promos.filter(models.ChannelPromotion.channel == self.channel.data)
        if request.args.get('id'):
            check_dupe = check_dupe.filter(models.ChannelPromotion.id != int(request.args.get('id')))
        if check_dupe.count():
            self.channel.errors = ['Channel is already promoted in this category']
            return

        if request.args.get('id'):
            promo = models.ChannelPromotion.query.get(int(request.args.get('id')))
            if promo.channel != self.channel.data:
                self.channel.errors = ['Channel cannot be changed once set']
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


class ChannelPromotion(AdminView):
    model_name = 'channel_promotion'
    model = models.ChannelPromotion

    form = ChannelPromotionForm

    column_formatters = dict(channel_origin=_format_channel_from, promo_state=_format_promo_state, appearing_in=_format_category_names)
    column_list = ('channel_rel', 'channel_origin', 'locale_rel', 'appearing_in', 'promo_state', 'position', 'date_start', 'date_end', 'date_added', 'date_updated')
    column_labels = dict(channel_rel='Channel', locale_rel='Target Locale', appearing_in='Target Category')
    column_filters = ('channel_rel', 'category_rel', 'locale_rel', 'position', 'date_added', 'date_updated', 'date_start', 'date_end')


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
    column_list = ('owner_rel', 'cover.url', 'date_created')
    column_filters = ('owner_rel',)
    form_columns = ('owner_rel', 'cover', 'cover_aoi')

    edit_template = 'admin/cover_art_edit.html'
    create_template = 'admin/cover_art_create.html'

    def update_model(self, form, model):
        prev_cover = model.cover.path
        success = super(UserCoverArt, self).update_model(form, model)
        if success and isinstance(form.cover.data, basestring):
            # Update channels that refer to this cover
            models.Channel.query.filter_by(owner=model.owner, cover=prev_cover).update(
                dict(cover=model.cover.path, cover_aoi=model.cover_aoi))
            self.session.commit()
        return success


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
    UserCoverArt, Channel, ChannelLocaleMeta, ChannelPromotion,
    ContentReport, ExternalCategoryMap]


def admin_views():
    for v in registered:
        yield v(name=v.__name__,
                endpoint=v.model_name,
                category='Video',)
