import re
import logging
from datetime import date
from cStringIO import StringIO
from werkzeug import MultiDict
import wtforms as wtf
from sqlalchemy import func
from flask import request, url_for, redirect, flash, jsonify
from flask.ext import login
from flask.ext.admin import expose, form
from wtforms.validators import ValidationError
from rockpack.mainsite import app, requests
from rockpack.mainsite.core.dbapi import commit_on_success, db
from rockpack.mainsite.core import youtube, ooyala
from rockpack.mainsite.core.s3 import s3connection
from rockpack.mainsite.helpers.db import resize_and_upload
from rockpack.mainsite.services.pubsubhubbub.api import subscribe
from rockpack.mainsite.services.video.models import (
    Source, Category, Video, VideoInstance, Channel)
from rockpack.mainsite.services.cover_art.models import UserCoverArt
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.services.oauth.api import RockRegistrationForm, send_password_reset
from .models import AdminLogRecord
from .base import AdminView


class ImportForm(form.BaseForm):
    source = form.Select2Field(coerce=int, validators=[wtf.validators.Required()])
    type = form.Select2Field(choices=(('video', 'Video'), ('user', 'User'), ('playlist', 'Playlist')),
                             validators=[wtf.validators.Required()])
    id = wtf.TextField(validators=[wtf.validators.Required()])
    category = form.Select2Field(coerce=int, default=-1)
    date_added = wtf.DateField(validators=[wtf.validators.Optional()], widget=form.DatePickerWidget())
    tags = wtf.TextField(validators=[wtf.validators.Optional()])
    cover = wtf.FileField(validators=[wtf.validators.Optional()])
    cover_url = wtf.TextField(validators=[wtf.validators.Optional(), wtf.validators.URL()])
    commit = wtf.HiddenField()
    user = wtf.TextField()
    channel = wtf.TextField()
    channel_description = wtf.TextAreaField(validators=[wtf.validators.Length(max=200)])

    def validate(self):
        if not super(ImportForm, self).validate():
            return

        if request.files.get('cover'):
            cover = request.files['cover']
        elif self.cover_url.data:
            cover = StringIO(requests.get(self.cover_url.data).content)
        else:
            cover = None

        if self.user.data:
            try:
                self.cover.data = resize_and_upload(cover, 'CHANNEL') if cover else ''
            except IOError, e:
                self.cover.errors = [str(e)]
                return
            UserCoverArt(cover=self.cover.data, owner=self.user.data).save()

        source_label = Source.id_to_label(self.source.data)

        if self.commit.data:
            # channel & category is required before commit
            if self.category.data == -1:
                self.category.errors = ['Please select a category']
                return
            if not self.channel.data and (source_label != 'youtube' or self.user.data):
                self.channel.errors = ['Please select a channel']
                return

        if source_label == 'youtube':
            get_data = getattr(youtube, 'get_%s_data' % self.type.data)
        elif source_label == 'ooyala' and self.type.data == 'video':
            get_data = ooyala.get_video_data
        else:
            self._errors = {'__all__': 'Unsupported source'}
            return

        try:
            # get all data only if we are ready to commit
            self.import_data = get_data(self.id.data, self.commit.data)
        except Exception, ex:
            logging.exception('Unable to import %s: %s', self.type.data, self.id.data)
            self._errors = {'__all__': 'Internal error: %r' % ex}
        else:
            return True


class UserForm(RockRegistrationForm):
    password = None
    date_of_birth = None
    email = None
    avatar = wtf.FileField(validators=[wtf.validators.Optional()])
    avatar_url = wtf.TextField(validators=[wtf.validators.Optional(), wtf.validators.URL()])
    description = wtf.TextField(validators=[wtf.validators.Optional()])
    site_url = wtf.TextField(validators=[wtf.validators.Optional(), wtf.validators.URL()])

    def validate_avatar(form, field):
        if not request.files.get('avatar'):
            raise ValidationError('No file chosen')


class ImportView(AdminView):

    @commit_on_success
    def _import_videos(self, form):
        for video in form.import_data.videos:
            video.rockpack_curated = True
            video.category = form.category.data
        count = Video.add_videos(form.import_data.videos, form.source.data)

        if not form.channel.data and not form.user.data:
            self._set_form_data_from_source(form)

        channelid = form.channel.data
        if channelid.startswith('_new:'):
            channel = Channel.create(
                title=channelid.split(':', 1)[1],
                owner=form.user.data,
                description=form.channel_description.data,
                cover=form.cover.data,
                category=form.category.data)
            self.record_action('created', channel)
        else:
            channel = Channel.query.get_or_404(channelid)
        channel.add_videos(
            form.import_data.videos,
            form.tags.data,
            category=form.category.data,
            date_added=form.date_added.data
        )
        self.record_action('imported', channel, '%d videos' % count)
        push_config = getattr(form.import_data, 'push_config', None)
        if push_config and channel.id:
            try:
                subscribe(push_config.hub, push_config.topic, channel.id)
            except Exception, e:
                flash('Unable to subscribe to channel: %s' % e.message, 'error')

        return count, channel

    def _set_form_data_from_source(self, form):
        username = form.import_data.videos[0].source_username
        site_url = 'http://www.youtube.com/%s' % username
        # check for existing user & channel
        matches = list(
            Channel.query.filter(func.lower(Channel.title).like('youtube channel:%')).
            join(User, (User.id == Channel.owner) &
                       (User.site_url == site_url) &
                       (User.username == username)).
            values(Channel.id, Channel.owner))
        if matches:
            form.channel.data, form.user.data = matches[0]
        else:
            user = youtube.get_user_profile_data(username)
            user_form = UserForm(MultiDict(dict(
                username=username,
                first_name=user.display_name or '',
                avatar_url=user.thumbnail,
                description=user.summary,
                site_url=site_url,
            )))
            form.user.data = self._create_user(user_form)
            form.channel.data = '_new:YouTube Channel: %s' % username

    def _create_user(self, form):
        if request.files.get('avatar'):
            avatar = resize_and_upload(request.files['avatar'], 'AVATAR')
        elif form.avatar_url.data:
            avatar_file = StringIO(requests.get(form.avatar_url.data).content)
            avatar = resize_and_upload(avatar_file, 'AVATAR')
        else:
            avatar = ''

        user = User(
            username=form.username.data.strip(),
            password_hash='',
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            description=form.description.data,
            site_url=form.site_url.data,
            email='',
            date_of_birth=date(1900, 1, 1),
            avatar=avatar,
            refresh_token='',
            locale=form.locale.data or 'en-us',
            is_active=True)
        self.record_action('created', user)
        db.session.add(user)
        db.session.commit()
        return user.id

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
        form.category.choices = [(-1, '')] +\
            list(Category.get_form_choices(data.get('locale') or 'en-us', True))

        user_form = UserForm(data, csrf_enabled=False)
        ctx['user_form'] = user_form
        ctx['form'] = form

        # pre-populate from parameters
        if request.args.get('tag'):
            form.tags.data = ','.join(request.args.getlist('tag'))

        if request.args.get('user'):
            user = list(User.query.filter_by(username=request.args.get('user')).values('id', 'username'))
            if user:
                form.user.data = user[0][0]
            else:
                form.user.data = ""

            if request.args.get('channeltitle'):
                channel = list(Channel.query.filter_by(
                    title=request.args.get('channeltitle'),
                    owner=form.user.data).values('id', 'title'))
                if channel:
                    form.channel.data = channel[0][0]
                else:
                    form.channel.data = '_new:' + request.args.get('channeltitle')

        if request.args.get('categoryname'):
            for choice in form.category.choices:
                if choice[1] == request.args.get('categoryname'):
                    form.category.data = choice[0]

        if 'source' in data:
            if form.commit.data and not form.user.data:
                if user_form.username.data:
                    if user_form.validate():
                        # update import form with new user
                        form.user.data = self._create_user(user_form)
                    else:
                        return self.render('admin/import.html', **ctx)
                else:
                    # User and channel will be created from source data
                    assert form.channel.data == ''

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
        exact_name = request.args.get('exact_name', '')
        if exact_name:
            return jsonify(User.query.filter(User.username == exact_name).values(User.id, User.username))
        prefix = request.args.get('prefix', '').lower()
        if prefix and re.match('^\w+$', prefix):
            return jsonify(User.query.filter(
                func.lower(User.username).like(prefix + '%')
            ).values(User.id, User.username))
        return []

    @expose('/channels.js')
    def channels(self):
        user = request.args.get('user', '')
        if 'user' in request.args.keys():
            if not re.match('^[\w-]+$', user):
                user = None
            return jsonify(Channel.get_form_choices(owner=user))
        exact_name = request.args.get('exact_name', '')
        if exact_name:
            channels = list(Channel.query.filter(Channel.title == exact_name).values(Channel.id, Channel.title))
            if not channels:
                channels = list(Channel.query.filter(Channel.id == exact_name).values(Channel.id, Channel.title))
            return jsonify(channels)
        prefix = request.args.get('prefix', '').lower()
        if prefix and re.match('^[!&#\w ]+$', prefix):
            return jsonify(Channel.query.filter(
                Channel.deleted == False,
                Channel.public == True,
                func.lower(Channel.title).like(prefix + '%')
            ).values(Channel.id, Channel.title))
        return []

    @expose('/video.js')
    def videos(self):
        vid = request.args.get('vid', '')
        if request.args.get('instance_id'):
            return jsonify(VideoInstance.query.join(Video).filter(VideoInstance.id == request.args.get('instance_id')).values(VideoInstance.video, Video.title))
        return jsonify(Video.query.filter(Video.id.like(vid + '%')).values(Video.id, Video.title))

    @expose('/tags.js')
    def tags(self):
        prefix = request.args.get('prefix', '')
        limit = int(request.args.get('size', 10))
        offset = int(request.args.get('start', 0))
        print limit, offset
        tags = []
        if prefix.startswith('cat-'):
            prefix = prefix[4:]
            categories = Category.query.filter(Category.name.like(prefix + '%')).\
                distinct().order_by(Category.name).limit(limit).offset(offset)
            tags.extend(('cat-%s' % n) for n, in categories.values(Category.name))
        elif len(prefix) > 2:
            instances = VideoInstance.query.filter(VideoInstance.tags.like(prefix + '%')).\
                distinct().order_by(VideoInstance.tags).limit(limit).offset(offset)
            tags.extend(set(instance_tags.split(',', 1)[0]
                            for instance_tags, in instances.values('tags')))
        return jsonify(tags=tags)

    @expose('/bookmarklet.js')
    def bookmarklet(self):
        return self.render('admin/import_bookmarklet.js')

    @expose('/coverart.js/', methods=('POST',))
    def coverart(self):
        if not User.query.get(request.form.get('owner')):
            return jsonify({'error': 'invalid owner'}), 400

        c = UserCoverArt(cover=resize_and_upload(request.files['cover'], 'CHANNEL'),
                         owner=request.form.get('owner')).save()
        return jsonify({'id': str(c.cover)})

    @expose('/resetpassword.js/', methods=('POST',))
    def resetpassword(self):
        try:
            user = User.query.filter(User.username == request.form.get('username')).one()
            if not user.email or '@' not in user.email:
                return jsonify({'error': "Can't reset password for %s: no valid email address" % user.id}), 400
            # Check if the user has a favourite - if this wasn't created
            # in the app it might not have one
            send_password_reset(user.id)
            fav = Channel.query.filter(
                Channel.owner == user.id,
                Channel.favourite == True,
                Channel.public == True)

            if not fav.count():
                title, description, cover = app.config['FAVOURITE_CHANNEL']
                Channel(
                    favourite=True,
                    title=title,
                    description=description,
                    cover=cover,
                    public=True,
                    owner=user.id
                ).save()
        except Exception, e:
            return jsonify({'error': str(e) + str(request.args)}), 400
        else:
            return jsonify({'success': True})


class UploadAcceptForm(form.BaseForm):
    path = wtf.HiddenField(validators=[wtf.validators.Required()])
    user = wtf.TextField(validators=[wtf.validators.Required()])
    channel = wtf.TextField(validators=[wtf.validators.Required()])
    title = wtf.TextField(validators=[wtf.validators.Required()])
    category = form.Select2Field(coerce=int, default=-1, validators=[wtf.validators.Required()])
    tags = wtf.TextField()

    def validate_channel(self, field):
        if field.data:
            owner = User.query.join(Channel).filter(
                Channel.id == field.data).value('username')
            if owner:
                self.owner_username = owner
            else:
                raise ValidationError('Channel not found')


class UploadView(AdminView):

    path_prefix = 'upload/'

    @property
    def bucket(self):
        if not getattr(self, '_bucket', None):
            self._bucket = s3connection().get_bucket(
                app.config['VIDEO_S3_BUCKET'], validate=False)
        return self._bucket

    @expose('/')
    def index(self):
        video_list = [
            dict(
                path=key.name[len(self.path_prefix):],
                size=key.size,
                link=key.generate_url(3600, force_http=True),
                last_modified=key.last_modified,
            )
            for key in self.bucket.list(self.path_prefix)
            if not key.name.endswith('manifest.txt') and not key.name.endswith('/')
        ]
        return self.render('admin/upload_review.html', video_list=video_list)

    @expose('/accept')
    def accept_form(self):
        path = request.args['video']
        basename, filename = path.rsplit('/', 1)
        meta = dict(path=path, title=filename.rsplit('.', 1)[0].replace('_', ' '))

        manifest = self.bucket.get_key(self.path_prefix + basename + '/manifest.txt')
        if manifest:
            for line in manifest.get_contents_as_string().split('\n'):
                if line.startswith(filename):
                    fields = line[len(filename):].strip().split('\t')
                    if fields:
                        meta['title'] = fields[0]
                    break

        form = UploadAcceptForm()
        form.category.choices = [(-1, '')] +\
            list(Category.get_form_choices('en-us', True))
        for field in meta:
            if hasattr(form, field):
                getattr(form, field).data = meta[field]

        return self.render('admin/upload_accept.html', form=form)

    @expose('/accept', methods=('POST',))
    def accept_process(self):
        form = UploadAcceptForm(request.form)
        form.category.choices = list(Category.get_form_choices('en-us', True))
        if form.validate():
            metadata = dict(label=form.owner_username, **form.data)
            dst = self._move_video(form.path.data, 'video/%s/' % form.owner_username)
            metadata['path'] = dst
            ooyala.create_asset_in_background(dst, metadata)
            flash('Processing "%s"...' % form.title.data)
            return redirect(url_for('review.index'))
        return self.render('admin/upload_accept.html', form=form)

    @expose('/reject.js', methods=('POST',))
    def reject(self):
        dst = self._move_video(request.form['video'], 'video/archive/')
        return jsonify(dict(path=dst))

    def _move_video(self, path, new_prefix):
        src = self.path_prefix + path
        dst = new_prefix + path
        self.bucket.copy_key(dst, self.bucket.name, src)
        self.bucket.delete_key(src)
        return dst
