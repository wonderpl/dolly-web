from datetime import datetime
from datetime import timedelta
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime, func
from sqlalchemy.orm import relationship, exc
from flask import abort
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import db, commit_on_success
from rockpack.mainsite.helpers import lazy_gettext as _
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.services.user.models import User, EXTERNAL_SYSTEM_NAMES
from . import exceptions, facebook


class ExternalToken(db.Model):

    __tablename__ = "external_token"

    id = Column(Integer, primary_key=True)
    user = Column(ForeignKey('user.id'), nullable=False)
    external_system = Column(Enum(*EXTERNAL_SYSTEM_NAMES, name='external_system_names'), nullable=False)
    external_token = Column(String(1024), nullable=False)
    external_uid = Column(String(1024), nullable=False)
    expires = Column(DateTime(), nullable=True)
    permissions = Column(String(1024), nullable=True)
    meta = Column(String(1024), nullable=True)

    user_rel = relationship('User', remote_side=[User.id], backref='external_tokens')

    def __unicode__(self):
        return '{} token for user <{}>'.format(self.external_system, self.user)

    @classmethod
    def user_from_token(cls, external_system, token):
        try:
            e = cls.query.filter_by(external_system=external_system,
                                    external_token=token).one()
        except exc.NoResultFound:
            return None
        return e.user_rel

    @classmethod
    def user_from_uid(cls, external_system, uid):
        try:
            e = cls.query.filter_by(external_system=external_system,
                                    external_uid=uid).one()
        except exc.NoResultFound:
            return None
        return e.user_rel

    @classmethod
    def update_token(cls, userid, eu):
        """Updates an existing token (or creates a new one) and returns the token object"""
        if eu.system not in EXTERNAL_SYSTEM_NAMES:
            raise exceptions.InvalidExternalSystem('{} is not a valid name'.format(eu.system))

        try:
            token = cls.query.filter_by(external_uid=eu.id, external_system=eu.system).one()
            token._existing = True
        except exc.NoResultFound:
            if ExternalToken.query.filter_by(user=userid, external_system=eu.system).count():
                abort(400, message=_('User already associated with account'))
            token = cls(user=userid,
                        external_system=eu.system,
                        external_uid=eu.id)
        else:
            if token.user != userid:
                app.logger.error('Token owner %s does not match update user: %s', token.user, userid)
                abort(400, message=_('External account mismatch'))

        token.external_token = eu.token
        token.expires = eu.expires
        token.permissions = eu.permissions
        token.meta = eu.meta

        # Fetch a long-lived token if we don't have an expiry,
        # or we haven't long to go until it does expire
        expiry_delta = timedelta(days=app.config.get('EXTERNAL_TOKEN_EXPIRY_THRESHOLD_DAYS', 1))
        if expiry_delta and (not token.expires or datetime.now() + expiry_delta > token.expires):
            new_eu = eu.get_new_token()
            token.external_token = new_eu.token
            token.expires = new_eu.expires

        return token.save()

    def get_resource_url(self, own=True):
        return url_for('userws.get_external_account', userid=self.user, id=self.id)
    resource_url = property(get_resource_url)


class ExternalFriend(db.Model):

    __tablename__ = "external_friend"

    id = Column(Integer, primary_key=True)
    user = Column(ForeignKey('user.id'), nullable=False)
    external_system = Column(Enum(*EXTERNAL_SYSTEM_NAMES, name='external_system_names'), nullable=False)
    external_uid = Column(String(1024), nullable=False)
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    name = Column(String(1024), nullable=False)
    avatar_url = Column(String(1024), nullable=False)
    has_ios_device = Column(Boolean)

    user_rel = relationship('User', remote_side=[User.id], backref='external_friends')

    @classmethod
    @commit_on_success
    def populate_facebook_friends(cls, userid, with_devices=True):
        """Update ExternalFriend mapping for facebook friends of the specified user"""
        # Don't update if existing data is less than an hour old or if no token available
        delta = ExternalFriend.query.filter_by(user=userid).value(
            func.now() - func.max(ExternalFriend.date_updated))
        if delta and (delta.days * 86400) + delta.seconds < 3600:
            return
        token = ExternalToken.query.filter_by(
            user=userid, external_system='facebook').first()
        if not token:
            return

        graph = facebook.GraphAPI(token.external_token)
        # XXX: Paging not handled. If a user has more than 1000 friends, tough!
        friends = graph.get_connections(token.external_uid, 'friends', limit=1000)
        external_friends = {}
        for friend in friends['data']:
            external_friends[friend['id']] = cls(
                user=userid,
                external_system='facebook',
                external_uid=friend['id'],
                name=friend['name'],
                avatar_url=facebook.FACEBOOK_PICTURE_URL % friend['id'],
                has_ios_device=False,
            )
        if not external_friends:
            return

        if with_devices:
            userdata = graph.get_objects(external_friends.keys(), fields='devices,picture.type(large)')
            for id, data in userdata.items():
                external_friends[id].has_ios_device =\
                    any(d['os'] == 'iOS' for d in data.get('devices', []))
                external_friends[id].avatar_url = data['picture']['data']['url']

        cls.query.filter_by(user=userid, external_system='facebook').delete()
        cls.query.session.add_all(external_friends.values())
