from sqlalchemy import (
    String, Column, Integer, Boolean, DateTime, ForeignKey, CHAR, event, func)
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
        q = cls.query
        if prefix:
            q = q.filter(cls.username.ilike(prefix + '%'))
        return q.values(cls.id, cls.username)

    @classmethod
    def get_from_username(cls, username):
        return cls.query.filter_by(username=username).one()


class UserActivity(db.Model):
    __tablename__ = 'user_activity'

    id = Column(Integer, primary_key=True)
    user = Column(CHAR(22), ForeignKey('user.id'), nullable=False)
    action = Column(String(16), nullable=False)
    date_actioned = Column(DateTime(), nullable=False, default=func.now())
    object_type = Column(String(16), nullable=False)
    object_id = Column(String(64), nullable=False)


event.listen(User, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z))
