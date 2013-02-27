import re
import uuid
from sqlalchemy import (
    String, Column, Integer, Boolean, DateTime, ForeignKey, CHAR, event, func)
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import generate_password_hash, check_password_hash
from flask import g
from rockpack.mainsite import app
from rockpack.mainsite.core.token import create_access_token
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import ImageType, add_base64_pk


class User(db.Model):
    __tablename__ = 'user'

    id = Column(CHAR(22), primary_key=True)
    username = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String(60), nullable=False)
    email = Column(String(254), nullable=False)
    first_name = Column(String(254), nullable=False)
    last_name = Column(String(254), nullable=False)
    avatar = Column(ImageType('AVATAR'), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default='true')
    refresh_token = Column(String(1024), nullable=False)

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

    def get_credentials(self):
        expires_in = app.config.get('ACCESS_TOKEN_EXPIRY', 3600)
        access_token = create_access_token(self.id, g.app_client_id, expires_in)
        return dict(
            token_type='Bearer',
            access_token=access_token,
            expires_in=expires_in,
            refresh_token=self.refresh_token,
            user_id=self.id,
        )

    @classmethod
    def suggested_username(cls, source_name):
        if not cls.query.filter_by(username=source_name).count():
            return source_name

        user = cls.query.filter(
                cls.username.like('{}%'.format(source_name))
                ).order_by("username desc").limit(1).one()
        match = re.findall(r"[a-zA-Z]+|\d+", user.username)

        try:
            postfix_number = int(match[-1])
        except TypeError:
            new_name = match + '1'
        else:
            new_name = ''.join(match[:-1]) + str(postfix_number + 1)
            return cls.suggested_username(new_name)

        return new_name

    @classmethod
    def sanitise_username(cls, name):
        return re.sub(r'\W+', '', name)

    @classmethod
    def create_with_channel(cls, username, first_name='',
            last_name='', email='', password=None, avatar=''):
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash='',
            refresh_token=uuid.uuid4().hex,
            avatar=avatar,
            is_active=True)
        user = user.save()
        if password:
            user.set_password(password)

        title, description, cover = app.config['FAVOURITE_CHANNEL']

        # Prevent circular import
        from rockpack.mainsite.services.video.models import Channel

        channel = Channel(
            title=title,
            description=description,
            cover=cover,
            owner=user.id)
        channel.save()

        return user

    @classmethod
    def create_from_external_system(
            cls, username, external_system, external_token, external_uid,
            first_name='', last_name='', email='', avatar=''):

        from rockpack.mainsite.services.oauth.models import ExternalToken

        if ExternalToken.query.filter_by(external_uid=external_uid).count():
            return None

        new_username = cls.suggested_username(
                cls.sanitise_username(username))

        user = cls.create_with_channel(new_username, first_name=first_name,
                last_name=last_name, email=email, avatar=avatar)

        ExternalToken.update_token(

            user, external_system, external_token, external_uid)
        return user


class UserActivity(db.Model):
    __tablename__ = 'user_activity'

    id = Column(Integer, primary_key=True)
    user = Column(CHAR(22), ForeignKey('user.id'), nullable=False)
    action = Column(String(16), nullable=False)
    date_actioned = Column(DateTime(), nullable=False, default=func.now())
    object_type = Column(String(16), nullable=False)
    object_id = Column(String(64), nullable=False)

event.listen(User, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z))
