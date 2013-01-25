import jinja2
from flask import url_for, flash, request, redirect, abort
from flask.ext import wtf
from flask.ext.admin import form, expose
from flask.ext.admin.model.form import InlineFormAdmin
from rockpack.mainsite.core import s3
from rockpack.mainsite.core.dbapi import session, commit_on_success
from rockpack.mainsite.admin.models import AdminView
from rockpack.mainsite.auth.models import User
from rockpack.mainsite.services.video import models


def _format_video_thumbnail(context, video, name):
    t = '<a target="_blank" href="%s"><img src="%s" width="160" height="90"/></a>'
    return jinja2.Markup(t % (video.player_link, video.default_thumbnail))


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

    column_display_pk = True


class ChannelForm(form.BaseForm):
    title = wtf.TextField()
    thumbnail_url = wtf.FileField()
    user = form.Select2Field(
        choices=[('', '')] + [(u.id, u.username) for u in User.get_form_choices()],
        validators=[wtf.validators.required()])


def _format_channel_thumbnail(context, channel, name):
    t = '<img src="%s" width="241" height="171"/>'
    return jinja2.Markup(t % channel.thumbnail_url_full) if channel.thumbnail_url else ''


class Channel(AdminView):
    model_name = 'channel'
    model = models.Channel

    column_list = ('title', 'owner_rel', 'thumbnail')
    column_formatters = dict(thumbnail=_format_channel_thumbnail)
    column_filters = ('title',)

    #list_template = 'admin/channel/list.html'

    def _save_channel_data(self, _form, update_id=None):
        t = ''
        if request.files and request.files.get('thumbnail_url').filename:
            t = s3.thumbnail_upload(
                request.files.get('thumbnail_url').filename,
                request.files.get('thumbnail_url').stream)
        channel = self.model()
        if update_id:
            channel = session.query(self.model).get(update_id)
        channel.title = _form.title.data
        channel.owner = _form.user.data
        if t:
            channel.thumbnail_url = t
        session.add(channel)

    @expose('/new/', ('GET', 'POST',))
    @commit_on_success
    def create_view(self):
        ctx = {}
        data = (request.form or request.args).copy()

        _form = ChannelForm(data, csrf_enabled=False)
        ctx['form'] = _form

        if request.method == 'POST':
            ctx['form'].user.default = ctx['form'].user.data
            if _form.validate():
                self._save_channel_data(_form)

                flash('Channel data saved')
                return redirect(url_for('channel.index_view'))

        return self.render(Channel.create_template, **ctx)

    @expose('/edit/', ('GET', 'POST',))
    @commit_on_success
    def edit_view(self):
        ctx = {}
        data = (request.form or request.args).copy()
        ctx['form'] = ChannelForm(csrf_enabled=False)
        if request.method == 'GET':
            if not data.get('id'):
                return abort

            channel = models.Channel.get(data.get('id'))
            ctx['form'] = ChannelForm(
                title=channel.title,
                thumbnail_url=channel.thumbnail_url)
            ctx['form'].user.data = channel.owner

        if request.method == 'POST':
            if ctx['form'].validate():
                self._save_channel_data(ctx['form'], update_id=request.args.get('id'))
                flash('Channel data updated')
                return redirect(url_for('channel.index_view'))

        return self.render(Channel.create_template, **ctx)


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
