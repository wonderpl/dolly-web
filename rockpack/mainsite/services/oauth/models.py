from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Enum)
from sqlalchemy.orm import relationship, exc

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
    def update_token(cls, user, external_system, token, external_uid):
        """ Updates an existing token (or creates a new one)
            and returns the token object """

        if external_system not in EXTERNAL_SYSTEM_NAMES:
            raise exceptions.InvalidExternalSystem('{} is not a valid name'.format(external_system))

        try:
            e = cls.query.filter_by(user=user.id, external_uid=external_uid, external_system=external_system).one()
        except exc.NoResultFound:
            c = cls(user=user.id,
                    external_system='facebook',
                    external_token=token,
                    external_uid=external_uid)
            return c.save()
        else:
            e.external_token = token
            return e.save()
