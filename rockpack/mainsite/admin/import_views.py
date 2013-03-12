import re
import logging
from datetime import date
from flask import request, url_for, redirect, flash, jsonify
from flask.ext import wtf, login
from flask.ext.admin import BaseView, expose, form
from wtforms.validators import ValidationError
from rockpack.mainsite.core.dbapi import commit_on_success, db
from rockpack.mainsite.core import youtube
from rockpack.mainsite.helpers.db import resize_and_upload
from rockpack.mainsite.services.pubsubhubbub.api import subscribe
from rockpack.mainsite.services.video.models import (
    Locale, Source, Category, Video, VideoLocaleMeta, Channel)
from rockpack.mainsite.services.user.models import User
from .models import AdminLogRecord


class ImportForm(form.BaseForm):
    source = form.Select2Field(coerce=int, validators=[wtf.validators.required()])
    type = form.Select2Field(choices=(('video', 'Video'), ('user', 'User'), ('playlist', 'Playlist')),
                             validators=[wtf.validators.required()])
    id = wtf.TextField(validators=[wtf.validators.required()])
    locale = form.Select2Field(default='en-gb')
    category = form.Select2Field(coerce=int, default=-1)
    commit = wtf.HiddenField()
    user = wtf.TextField()
    channel = wtf.TextField()
    channel_description = wtf.TextAreaField()

    def validate(self):
        if not super(ImportForm, self).validate():
            return
        if self.commit.data and self.category.data == -1:
            # category is required before commit
            self.category.errors = ['Please select a category']
            return
        if self.source.data == 1:   # youtube
            get_data = getattr(youtube, 'get_%s_data' % self.type.data)
            try:
                # get all data only if we are ready to commit
                self.import_data = get_data(self.id.data, self.commit.data)
            except Exception, ex:
                logging.exception('Unable to import %s: %s', self.type.data, self.id.data)
                self._errors = {'__all__': 'Internal error: %r' % ex}
            else:
                return True


class UserForm(form.BaseForm):
    username = wtf.TextField(validators=[wtf.validators.required()])
    first_name = wtf.TextField(validators=[wtf.validators.required()])
    last_name = wtf.TextField(validators=[wtf.validators.required()])
    email = wtf.TextField(validators=[wtf.validators.required()])
    avatar = wtf.FileField()

    def validate_avatar(form, field):
        if not request.files.get('avatar'):
            raise ValidationError('No file chosen')


class ImportView(BaseView):

    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()

    @commit_on_success
    def _import_videos(self, form):
        count = Video.add_videos(
            form.import_data.videos,
            form.source.data,
            form.locale.data,
            form.category.data)

        channel = form.channel.data   # XXX: Need to validate?
        user = form.user.data
        if channel and user:
            if channel.startswith('_new:'):
                channel = Channel.create(
                    title=channel.split(':', 1)[1],
                    owner=user,
                    description=form.channel_description.data,
                    cover='',
                    locale=form.locale.data,
                    category=form.category.data)
                self.record_action('created', channel)
            else:
                channel = Channel.query.get(channel)
            channel.add_videos(form.import_data.videos)
            self.record_action('imported', channel, '%d videos' % count)
            push_config = form.import_data.push_config
            if push_config and channel.id:
                subscribe(push_config.hub, push_config.topic, channel.id)
        else:
            channel = None

        return count, channel

    def _create_user(self, form):
        if 'avatar' in request.files:
            avatar = resize_and_upload(request.files['avatar'], 'AVATAR')
        else:
            avatar = ''
        user = User(
            username=form.username.data,
            password_hash='',
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            date_of_birth=date(1900, 1, 1),
            avatar=avatar,
            refresh_token='',
            is_active=True)
        self.record_action('created', user)
        db.session.add(user)
        db.session.commit()
        return user

    def record_action(self, action, model, value=None):
        db.session.add(AdminLogRecord(
            username=login.current_user.username,
            action=action,
            model=model.__class__.__name__,
            instance_id=unicode(model.id),
            value=value or unicode(model),
        ))

    @expose('/', ('GET', 'POST'))
    def index(self):
        ctx = {}
        data = (request.form or request.args).copy()

        # Ugly reverse mapping of source labels
        source = data.get('source')
        if source:
            for id, label in Source.get_form_choices():
                if source == label:
                    data['source'] = id

        form = ImportForm(data, csrf_enabled=False)
        form.source.choices = list(Source.get_form_choices())
        form.locale.choices = list(Locale.get_form_choices())
        form.category.choices = [(-1, '')] +\
            list(Category.get_form_choices(form.locale.data))

        user_form = UserForm(data, csrf_enabled=False)
        ctx['user_form'] = user_form
        ctx['form'] = form

        if 'source' in data:
            if form.commit.data and not form.user.data:
                if not user_form.validate():
                    return self.render('admin/import.html', **ctx)

                user = self._create_user(user_form)
                # update import form with new user
                form.user.data = user.id

            if form.validate():
                if form.commit.data:
                    count, channel = self._import_videos(form)
                    if channel and channel.id:
                        url = '%s?id=%s' % (url_for('channel.edit_view'), channel.id)
                    else:
                        url = url_for('video.index_view')
                        if form.type.data == 'playlist':
                            url += '?flt0_0=' + form.id.data
                    flash('Imported %d videos' % count)
                    return redirect(url)
                else:
                    ctx['import_preview'] = form.import_data
                    form.commit.data = 'true'

        return self.render('admin/import.html', **ctx)

    @expose('/users.js')
    def users(self):
        prefix = request.args.get('prefix', '')
        exact_name = request.args.get('exact_name', '')
        if exact_name:
            return jsonify(User.query.filter(User.username==exact_name).values(User.id, User.username))
        if not re.match('^\w+$', prefix):
            prefix = None
        return jsonify(User.get_form_choices(prefix=prefix))

    @expose('/channels.js')
    def channels(self):
        user = request.args.get('user', '')
        if user:
            if not re.match('^[\w-]+$', user):
                user = None
            return jsonify(Channel.get_form_choices(owner=user))
        prefix = request.args.get('prefix', '')
        exact_name = request.args.get('exact_name', '')
        if exact_name:
            return jsonify(Channel.query.filter(Channel.title==exact_name).values(Channel.id, Channel.title))
        if prefix:
            if not re.match('^[\w ]+$', prefix):
                prefix = None
            return jsonify(Channel.query.filter(
                    Channel.title.ilike(prefix + '%')).values(Channel.id, Channel.title))
        return []

    @expose('/video.js')
    def videos(self):
        vid = request.args.get('vid', '')
        if request.args.get('instance_id'):
            return jsonify(VideoLocaleMeta.query.join(Video).filter(VideoLocaleMeta.id==request.args.get('instance_id')).values(VideoLocaleMeta.video, Video.title))
        return jsonify(Video.query.filter(Video.id.ilike(vid + '%')).values(Video.id, Video.title))

    @expose('/bookmarklet.js')
    def bookmarklet(self):
        return self.render('admin/import_bookmarklet.js')
