import re
import logging
from flask import request, url_for, redirect, flash, jsonify
from flask.ext import wtf, login
from flask.ext.admin import BaseView, expose, form
from rockpack.mainsite.core import youtube
from rockpack.mainsite.services.video.models import (
    Locale, Source, Category, Video, Channel)
from rockpack.mainsite.auth.models import User
from rockpack.mainsite.core.dbapi import commit_on_success


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


class ImportView(BaseView):

    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()

    @expose('/', ('GET', 'POST'))
    @commit_on_success
    def index(self):
        ctx = {}
        data = (request.form or request.args).copy()
        source_choices = Source.get_form_choices()

        # Ugly reverse mapping of source labels
        source = data.get('source')
        if source:
            for id, label in source_choices:
                if source == label:
                    data['source'] = id

        form = ImportForm(data, csrf_enabled=False)
        form.source.choices = source_choices
        form.locale.choices = Locale.get_form_choices()
        form.category.choices = [(-1, '')] +\
            list(Category.get_form_choices(form.locale.data))

        ctx['form'] = form
        if 'source' in data and form.validate():
            if form.commit.data:
                count = Video.add_videos(
                    form.import_data.videos,
                    form.source.data,
                    form.locale.data,
                    form.category.data)

                channel = form.channel.data   # XXX: Need to validate?
                user = form.user.data
                if channel and user:
                    if channel.startswith('_new:'):
                        channel = Channel(title=channel.split(':', 1)[1],
                                          owner=user, thumbnail_url='')
                    else:
                        channel = Channel.get(channel)
                    channel.add_videos(form.import_data.videos)

                flash('Imported %d videos' % count)
                return redirect(url_for('video.index_view'))
            else:
                ctx['import_preview'] = form.import_data
                form.commit.data = 'true'

        return self.render('admin/import.html', **ctx)

    @expose('/users.js')
    def users(self):
        prefix = request.args.get('prefix', '')
        if not re.match('^\w+$', prefix):
            prefix = None
        return jsonify(User.get_form_choices(prefix=prefix))

    @expose('/channels.js')
    def channels(self):
        user = request.args.get('user', '')
        if not re.match('^[\w-]+$', user):
            user = None
        return jsonify(Channel.get_form_choices(owner=user))

    @expose('/bookmarklet.js')
    def bookmarklet(self):
        return self.render('admin/import_bookmarklet.js')
