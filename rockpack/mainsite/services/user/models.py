from sqlalchemy import (
    String, Column, Integer, Boolean, DateTime, ForeignKey, CHAR, event, func)
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import generate_password_hash, check_password_hash
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import ImageType, add_base64_pk


class LazyUser(object):
    def __init__(self, user_id):
        self.user_id = user_id
        self.user = None

    def __getattr__(self, key):
        if not getattr(self, 'user'):
            print 'setting user'
            setattr(self, 'user', User.query.get(self.user_id))
        return getattr(self.user, key)


class User(db.Model):
    __tablename__ = 'user'

    id = Column(CHAR(22), primary_key=True)
    username = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String(60), nullable=True)
    email = Column(String(254), nullable=False)
    first_name = Column(String(254), nullable=False)
    last_name = Column(String(254), nullable=False)
    avatar = Column(ImageType('AVATAR'), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default='true')
    refresh_token = Column(String(1024), nullable=True)

    channels = relationship('Channel')

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
        try:
            return cls.query.filter_by(username=username).one()
        except NoResultFound:
            return None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.save()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def display_name(self):
        # XXX: Needs to be more general?
        if self.first_name:
            return u'%s %s' % (self.first_name, self.last_name)
        else:
            return self.username


class UserActivity(db.Model):
    __tablename__ = 'user_activity'

    id = Column(Integer, primary_key=True)
    user = Column(CHAR(22), ForeignKey('user.id'), nullable=False)
    action = Column(String(16), nullable=False)
    date_actioned = Column(DateTime(), nullable=False, default=func.now())
    object_type = Column(String(16), nullable=False)
    object_id = Column(String(64), nullable=False)

event.listen(User, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z))
