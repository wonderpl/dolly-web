from urllib import urlencode
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.exc import IntegrityError
from rockpack.mainsite.core.dbapi import db, commit_on_success
from rockpack.mainsite.helpers.db import make_id
from rockpack.mainsite.helpers.urls import url_for, slugify
from rockpack.mainsite.services.video.models import Channel, VideoInstance


class ShareLink(db.Model):
    __tablename__ = 'share_link'

    id = Column(String(8), primary_key=True)
    user = Column(ForeignKey('user.id'), nullable=False)
    date_created = Column(DateTime(), nullable=False, default=func.now())
    object_type = Column(String(16), nullable=False)
    object_id = Column(String(64), nullable=False)
    click_count = Column(Integer, nullable=False, default=0)

    @classmethod
    def create(cls, user, object_type, object_id):
        # 5 bytes of random data for id = 2**(8*5) ~= 1 billion ids
        # Shouldn't get (m)any collisions at that size but we try to
        # handle it anyway.
        link = cls(user=user, object_type=object_type, object_id=object_id)
        session = cls.query.session
        for i in xrange(3):
            link.id = make_id(length=5)
            session.add(link)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                if i < 2:
                    continue
                else:
                    # Automatically increase id length?
                    raise Exception('Unable to select new link id')
            else:
                break
        return link

    @classmethod
    @commit_on_success
    def increment_click_count(cls, id):
        cls.query.filter_by(id=id).update({cls.click_count: cls.click_count + 1})

    def get_resource_url(self, own=False):
        return url_for('share_redirect', linkid=self.id)

    def process_redirect(self, increment_click_count=True):
        """Construct redirect url for link and record the click."""
        channel = Channel.query.with_entities(Channel.id, Channel.title)
        if self.object_type == 'video_instance':
            channel = channel.filter(
                (VideoInstance.channel == Channel.id) &
                (VideoInstance.id == self.object_id))
            params = dict(video=self.object_id)
        else:
            channel = channel.filter_by(id=self.object_id)
            params = dict()
        # TODO: Do something more friendly than throw a 404?
        channelid, title = channel.first_or_404()
        url = url_for('channel', slug=slugify(title) or '-', channelid=channelid)
        if params:
            # TODO: add utm tracking params for google analytics
            url += '?' + urlencode(params)
        if increment_click_count:
            ShareLink.increment_click_count(self.id)
        return {'url': url,
                'channel': channelid,
                'video': params.get('video', None)}
