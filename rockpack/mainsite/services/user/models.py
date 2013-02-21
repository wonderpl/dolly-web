from flask import g
from werkzeug.security import (
        generate_password_hash,
        check_password_hash)

from sqlalchemy import (
    String,
    Column,
    Boolean,
    event,
    CHAR,
)

from sqlalchemy.orm.exc import NoResultFound

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
        try:
            return g.session.query(cls).filter_by(username=username).one()
        except NoResultFound:
            return None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.save()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


event.listen(User, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z))
