import json
from sqlalchemy.orm import contains_eager
from sqlalchemy.sql.expression import desc
from flask.ext.admin import form
from flask.ext import wtf
from flask import g, jsonify, request, url_for, Response, abort
from wtforms.validators import ValidationError

from rockpack.mainsite.core.webservice import WebService
from rockpack.mainsite.core.webservice import expose
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.admin.import_views import create_channel
from rockpack.mainsite.helpers.http import cache_for


def _filter_by_category(query, type, category_id):
    """Filter given query by the specified category.
    If top-level category given, then filter by all sub categories.
    """
    sub_cats = list(models.Category.query.filter_by(parent=category_id).
                    values(models.Category.id))
    cat_ids = zip(*sub_cats)[0] if sub_cats else [category_id]
    return query.filter(type.category.in_(cat_ids))


def channel_dict(channel):
    sizes = ['thumbnail_large', 'thumbnail_small', 'background']
    images = {'cover_%s_url' % s: getattr(channel.cover, s) for s in sizes}
    url = url_for('UserAPI_api.channel_item',
                  userid=channel.owner_rel.id,
                  channelid=channel.id,
                  _external=True)
    ch_data = dict(
        id=channel.id,
        resource_url=url,
        title=channel.title,
        thumbnail_url=channel.cover.thumbnail_large,
        description=channel.description,
        subscribe_count=0,  # TODO: implement this for real
        owner=dict(
            id=channel.owner_rel.id,
            name=channel.owner_rel.username,
            avatar_thumbnail_url=channel.owner_rel.avatar.thumbnail_small,
        )
    )
    ch_data.update(images)
    return ch_data


def get_local_channel(locale, paging, **filters):
    metas = models.ChannelLocaleMeta.query.filter_by(visible=True, locale=locale)
    if filters.get('category'):
        metas = _filter_by_category(metas, models.ChannelLocaleMeta, filters['category'])
    if filters.get('query'):
        # The contains_eager clause is necessary when filtering on
        # a lazy loaded join.
        metas = metas.join(models.Channel).\
            options(contains_eager(models.ChannelLocaleMeta.channel_rel))
        metas = metas.filter(models.Channel.title.ilike('%%%s%%' % filters['query']))

    total = metas.count()
    offset, limit = paging
    metas = metas.offset(offset).limit(limit)
    channel_data = []
    for position, meta in enumerate(metas, 1):
        item = dict(
            position=position,
            id=meta.id,
            category=meta.category,
        )
        item.update(channel_dict(meta.channel_rel))
        channel_data.append(item)

    return channel_data, total


def check_present(form, field):
    if field.name not in request.form:
        raise ValidationError('{} must be present'.format(field.data))


def verify_id_on_model(model):
    def f(form, field):
        if field.data:
            if not model.query.get(field.data):
                raise ValidationError('Invalid {} "{}"'.format(field, field.data))
    return f


# TODO: check if we've duplicated this in import view
# and refactor as appropriate
class ChannelForm(form.BaseForm):
    title = wtf.TextField(validators=[check_present])
    description = wtf.TextField(validators=[check_present])
    owner = wtf.TextField(validators=[check_present, verify_id_on_model(User)])
    locale = wtf.TextField(validators=[check_present, verify_id_on_model(models.Locale)])
    category = wtf.TextField(validators=[check_present, verify_id_on_model(models.Category)])


class ChannelAPI(WebService):

    endpoint = '/channels'

    @expose('/', methods=('GET',))
    @cache_for(seconds=300)
    def channel_list(self):
        data, total = get_local_channel(self.get_locale(),
                                        self.get_page(),
                                        category=request.args.get('category'))
        response = jsonify({
            'channels': {
            'items': data,
            'total': total},
        })
        return response

    @expose('/<string:channel_id>/', methods=('PUT',))
    def channel_item(self, channel_id):
        channel = models.Channel.query.get(channel_id)
        if not channel:
            abort(404)

        form = ChannelForm(request.form, csrf_enabled=False)
        if not form.validate():
            return Response(json.dumps(form.errors), 400)

        channel.title = form.title.data
        channel.description = form.description.data
        channel.locale = form.locale.data
        channel.category = form.category.data
        channel.save()

        return Response(json.dumps({
            'channels': {
                'items': [channel_dict(channel)],
                'total': 1},
            }), mimetype='application/json', status=200)

    @expose('/', methods=('POST',))
    def channel_item_edit(self):
        form = ChannelForm(request.form, csrf_enabled=False)
        if form.validate():
            # TODO: validate user id against access token
            # once it's merged in
            cover = request.files.get('cover', '')
            channel = create_channel(title=form.title.data,
                    description=form.description.data,
                    owner=form.owner.data,
                    locale=form.locale.data,
                    category=form.category.data,
                    cover=cover).save()

            # TODO: change this to reflect the upcoming
            # return values allowed in @expose
            return Response(json.dumps({
                'channels': {
                'items': [channel_dict(channel)],
                'total': 1},
            }), mimetype='application/json', status=201)

        return Response(json.dumps({'errors': form.errors}),
                status=400)


def video_dict(instance):
    # TODO: unfudge this
    thumbnail_url = None
    for t in instance.thumbnails:
        if not thumbnail_url:
            thumbnail_url = t.url
        if t.url.count('mqdefault.jpg'):
            thumbnail_url = t.url
            break

    return dict(
        id=instance.id,
        source=['rockpack', 'youtube'][instance.source],    # TODO: read source map from db
        source_id=instance.source_videoid,
        view_count=instance.view_count,
        star_count=instance.star_count,
        thumbnail_url=thumbnail_url,
    )


def get_local_videos(loc, paging, with_channel=True, **filters):
    videos = g.session.query(models.VideoInstance, models.Video,
                             models.VideoLocaleMeta).join(models.Video)

    if filters.get('channel'):
        # If selecting videos from a specific channel then we want all videos
        # except those explicitly visible=False for the requested locale.
        # Videos without a locale metadata record will be included.
        videos = videos.outerjoin(models.VideoLocaleMeta,
                    (models.Video.id == models.VideoLocaleMeta.video) &
                    (models.VideoLocaleMeta.locale == loc)).\
            filter((models.VideoLocaleMeta.visible == True) |
                   (models.VideoLocaleMeta.visible == None)).\
            filter(models.VideoInstance.channel == filters['channel'])
    else:
        # For all other queries there must be an metadata record with visible=True
        videos = videos.join(models.VideoLocaleMeta,
                (models.Video.id == models.VideoLocaleMeta.video) &
                (models.VideoLocaleMeta.locale == loc) &
                (models.VideoLocaleMeta.visible == True))

    if filters.get('category'):
        videos = _filter_by_category(videos, models.VideoLocaleMeta, filters['category'][0])

    if filters.get('star_order'):
        videos = videos.order_by(desc(models.VideoLocaleMeta.star_count))

    if filters.get('date_order'):
        videos = videos.order_by(desc(models.VideoInstance.date_added))

    total = videos.count()
    offset, limit = paging
    videos = videos.offset(offset).limit(limit)
    data = []
    for position, v in enumerate(videos, offset):
        item = dict(
            position=position,
            date_added=v.VideoInstance.date_added.isoformat(),
            video=video_dict(v.Video),
            id=v.VideoInstance.id,
            title=v.Video.title,
        )
        if with_channel:
            item['channel'] = channel_dict(v.VideoInstance.video_channel)
        data.append(item)
    return data, total


class VideoAPI(WebService):

    endpoint = '/videos'

    @expose('/', methods=('GET',))
    @cache_for(seconds=300)
    def video_list(self):
        data, total = get_local_videos(self.get_locale(), self.get_page(), star_order=True, **request.args)
        response = jsonify({'videos': {'items': data, 'total': total}})
        return response


class CategoryAPI(WebService):

    endpoint = '/categories'

    @staticmethod
    def cat_dict(instance):
        data = dict(
            id=str(instance.id),
            name=instance.name,
            priority=instance.priority,
        )
        for c in instance.children:
            data.setdefault('sub_categories', []).append(CategoryAPI.cat_dict(c))
        return data

    def _get_cats(self, **filters):
        cats = models.Category.query.filter_by(locale=self.get_locale(), parent=None)
        return [self.cat_dict(c) for c in cats]

    @expose('/', methods=('GET',))
    @cache_for(seconds=3600)
    def category_list(self):
        data = self._get_cats(**request.args)
        response = jsonify({'categories': {'items': data}})
        return response
