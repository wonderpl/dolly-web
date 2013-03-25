from datetime import datetime, timedelta
import hmac
import hashlib
import requests
from sqlalchemy import (Column, Integer, String, Boolean,
                        DateTime, ForeignKey, UniqueConstraint, func)
from sqlalchemy.orm import relationship
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import make_id
from rockpack.mainsite.helpers.urls import url_for


LEASE_SECONDS = 60 * 60 * 24


class Subscription(db.Model):

    __tablename__ = 'push_subscription'
    __table_args__ = (
        UniqueConstraint('hub', 'topic'),
    )

    id = Column(Integer, primary_key=True)
    hub = Column(String(1024), nullable=False)
    topic = Column(String(1024), nullable=False)
    verify_token = Column(String(1024), nullable=False)
    verified = Column(Boolean(), nullable=False, default=False)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    lease_expires = Column(DateTime(), nullable=False)
    channel_id = Column('channel', ForeignKey('channel.id'), nullable=False)

    channel = relationship('Channel')

    @property
    def secret(self):
        return hmac.new(app.secret_key, self.hub).hexdigest()

    def verify(self, topic, verify_token, lease_seconds, challenge):
        if self.topic == topic and self.verify_token == verify_token:
            self.verified = True
            if lease_seconds:
                self.lease_expires = datetime.now() + timedelta(seconds=int(lease_seconds))
            self.save()
            return challenge

    def check_signature(self, signature, data):
        digest = hmac.new(self.secret, data, hashlib.sha1).hexdigest()
        return signature == 'sha1=' + digest

    def subscribe(self):
        if not self.verify_token:
            self.verify_token = make_id()
        if not self.id:
            self.lease_expires = datetime.now() + timedelta(seconds=LEASE_SECONDS)
            self.id = self.save().id
        self._ping_hub('subscribe')

    def unsubscribe(self):
        self._ping_hub('unsubscribe')

    def _ping_hub(self, mode):
        callback_url = url_for('pubsubhubbubws.callback')
        data = {
            'hub.callback': callback_url + '?id=' + str(self.id),
            'hub.mode': mode,
            'hub.topic': self.topic,
            'hub.verify': 'async',
            'hub.lease_seconds': LEASE_SECONDS,
            'hub.verify_token': self.verify_token,
            'hub.secret': self.secret,
        }
        response = requests.post(self.hub, data)
        response.raise_for_status()
        return response
