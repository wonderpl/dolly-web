from sqlalchemy import Column, Integer, ForeignKey, CHAR
from sqlalchemy.orm import relationship
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import ImageType
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.services.user.models import User


class RockpackCoverArt(db.Model):

    __tablename__ = 'rockpack_cover_art'

    id = Column(Integer, primary_key=True)
    cover = Column(ImageType('CHANNEL'), nullable=False)
    locale = Column(ForeignKey('locale.id'), nullable=False)
    category = Column(ForeignKey('category.id'), nullable=True)

    locale_rel = relationship('Locale', backref='cover_art')
    category_rel = relationship('Category', backref='cover_art')


class UserCoverArt(db.Model):

    __tablename__ = 'user_cover_art'

    id = Column(Integer, primary_key=True)
    cover = Column(ImageType('CHANNEL'), nullable=False)
    owner = Column(CHAR(22), ForeignKey('user.id'), nullable=False)

    owner_rel = relationship(User, primaryjoin=(owner == User.id))

    def get_resource_url(self, own=False):
        view = 'userws.delete_cover_art_item' if own else 'userws.redirect_cover_art_item'
        return url_for(view, userid=self.owner, ref=self.cover)
    resource_url = property(get_resource_url)
