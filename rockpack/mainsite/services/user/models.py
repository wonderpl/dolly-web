from flask import g

from sqlalchemy import (
    String,
    Column,
    Integer,
    ForeignKey,
    Boolean,
    event,
    CHAR,
)

from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import ImageType, add_base64_pk


class User(db.Model):
    __tablename__ = 'user'

    id = Column(CHAR(22), primary_key=True)
    username = Column(String(254), unique=True, nullable=False)
    email = Column(String(254), nullable=False)
    first_name = Column(String(254), nullable=False)
    last_name = Column(String(254), nullable=False)
    avatar = Column(ImageType('AVATAR'), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default='true')

    def __unicode__(self):
        return self.username

    @classmethod
    def get_form_choices(cls, prefix=None):
        q = g.session.query(cls.id, cls.username)
        if prefix:
            q = q.filter(cls.username.ilike(prefix + '%'))
        return q

    @classmethod
    def get_from_username(cls, username):
        return g.session.query(cls).filter_by(username=username).one()


event.listen(User, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z))

