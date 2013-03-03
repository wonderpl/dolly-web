from datetime import datetime
from datetime import timedelta
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Enum,
    DateTime)
from sqlalchemy.orm import relationship, exc

from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.services.user.models import User
from . import exceptions


EXTERNAL_SYSTEM_NAMES = ('facebook',)


class ExternalToken(db.Model):

    __tablename__ = "external_token"

    id = Column(Integer, primary_key=True)
    user = Column(ForeignKey('user.id'), nullable=False)
    external_system = Column(Enum(*EXTERNAL_SYSTEM_NAMES, name='external_system_names'), nullable=False)
    external_token = Column(String(1024), nullable=False)
    external_uid = Column(String(1024), nullable=False)
    expires = Column(DateTime(), nullable=True)

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
    def update_token(cls, user, eu):
        """ Updates an existing token (or creates a new one)
            and returns the token object """

        if eu.system not in EXTERNAL_SYSTEM_NAMES:
            raise exceptions.InvalidExternalSystem('{} is not a valid name'.format(eu.system))

        try:
            e = cls.query.filter_by(external_uid=eu.id, external_system=eu.system).one()
            if e.user != user.id:
                error = 'Token owner <user:{}> does not match id {}'.format(e.user, user.id)
                app.logger.error(error)
                raise exceptions.InvalidUserForExternalToken(error)
        except exc.NoResultFound:
            e = cls(user=user.id,
                    external_system='facebook',
                    external_token=eu.token,
                    external_uid=eu.id)

        # Fetch a long-lived token if we don't have an expiry,
        # or we haven't go long until it does expire,
        # or if the tokens differ.
        def _expired_token(expires):
            if not expires:
                return True
            if datetime.utcnow() + timedelta(days=1) > expires:
                return True
            return False

        if _expired_token(e.expires):
            new_eu = eu.get_new_token()
            e.external_token = new_eu.token
            e.expires = new_eu.expires
        return e.save()
