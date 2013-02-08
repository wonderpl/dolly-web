from sqlalchemy import (
        Column,
        Integer,
        ForeignKey,
        CHAR)

from sqlalchemy.orm import relationship

from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import ImageType
from rockpack.mainsite.auth.models import User


class RockpackCoverArt(db.Model):

    __tablename__ = 'rockpack_cover_art'

    id = Column(Integer, primary_key=True)
    cover = Column(ImageType('CHANNEL'), nullable=False)
    locale = Column(ForeignKey('locale.id'), nullable=False)

    locale_rel = relationship('Locale', backref='cover_art')


class UserCoverArt(db.Model):

    __tablename__ = 'user_cover_art'

    id = Column(Integer, primary_key=True)
    cover = Column(ImageType('CHANNEL'), nullable=False)
    owner = Column(CHAR(22), ForeignKey('user.id'), nullable=False)

    owner_rel = relationship(User, primaryjoin=(owner==User.id))
