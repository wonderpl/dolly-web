import re
import uuid
from sqlalchemy import (
    String, Column, Integer, Boolean, Date, DateTime, ForeignKey,
    Text, Enum, CHAR, PrimaryKeyConstraint, event, func)
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask import g
from rockpack.mainsite import app
from rockpack.mainsite.core.token import create_access_token
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import ImageType, add_base64_pk, resize_and_upload
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.core.es.api import add_user_to_index


USER_FLAGS = 'facebook_autopost_star', 'facebook_autopost_add'
EXTERNAL_SYSTEM_NAMES = 'facebook', 'twitter', 'google', 'apns'
GENDERS_MAP = {'m': 'male', 'f': 'female'}
GENDERS = GENDERS_MAP.keys()


class User(db.Model):
    __tablename__ = 'user'

    id = Column(CHAR(22), primary_key=True)
    username = Column(String(52), unique=True, nullable=False)
    password_hash = Column(String(60), nullable=False)
    email = Column(String(254), nullable=False)
    first_name = Column(String(32), nullable=False)
    last_name = Column(String(32), nullable=False)
    date_of_birth = Column(Date())
    avatar = Column(ImageType('AVATAR'), nullable=False)
    gender = Column(Enum(*GENDERS, name='gender_enum'), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default='true', default=True)
    refresh_token = Column(String(1024), nullable=False)
    username_updated = Column(Boolean, nullable=False, server_default='false', default=False)
    date_joined = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    display_fullname = Column(Boolean, nullable=False, server_default='true', default=True)

    locale = Column(ForeignKey('locale.id'), nullable=False, server_default='')

    channels = relationship('Channel')
    flags = relationship('UserFlag')
    activity = relationship('UserActivity', backref='actor')

    def __unicode__(self):
        return self.username

    def __repr__(self):
        return 'User(id={u.id!r}, username={u.username!r})'.format(u=self)

    @classmethod
    def get_form_choices(cls, prefix=None):
        q = cls.query
        if prefix:
            q = q.filter(cls.username.ilike(prefix + '%'))
        return q.values(cls.id, cls.username)

    @classmethod
    def get_from_credentials(cls, username, password):
        if '@' in username:
            filter = dict(email=username)
        else:
            filter = dict(username=username)
        # XXX: email field doesn't have unique constraint - for now we
        # check each record for matching password but we could consider
        # taking first only or applying unique constraint
        for user in cls.query.filter_by(is_active=True, **filter):
            if password is None or user.check_password(password):
                return user

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def display_name(self):
        # XXX: Needs to be more general?
        if self.first_name and self.display_fullname:
            return u'%s %s' % (self.first_name, self.last_name)
        else:
            return self.username

    def get_resource_url(self, own=False):
        view = 'userws.own_user_info' if own else 'userws.user_info'
        return url_for(view, userid=self.id)
    resource_url = property(get_resource_url)

    def get_credentials(self):
        expires_in = app.config.get('ACCESS_TOKEN_EXPIRY', 3600)
        # This is mostly used in oauth/api.py where `app_client_id` is set in the
        # `check_client_authorization` decorator from the Basic auth token. `client_id`
        # is set in `check_authorization` from the Bearer token.
        try:
            client_id = g.app_client_id
        except AttributeError:
            client_id = g.authorized.clientid
        access_token = create_access_token(self.id, client_id, expires_in)
        return dict(
            token_type='Bearer',
            access_token=access_token,
            expires_in=expires_in,
            refresh_token=self.refresh_token,
            user_id=self.id,
            resource_url=self.get_resource_url(own=True),
        )

    @classmethod
    def change_password(cls, user, new_pwd):
        user.set_password(new_pwd)
        user.reset_refresh_token()
        user = user.save()

    @classmethod
    def suggested_username(cls, source_name):
        if not username_exists(source_name):
            return source_name

        user = cls.query.filter(
            cls.username.like('{}%'.format(source_name))
        ).order_by("username desc").limit(1).first()
        match = re.findall(r"[a-zA-Z]+|\d+", user.username if user else source_name)

        try:
            postfix_number = int(match[-1])
        except (ValueError, TypeError):
            new_name = ''.join(match) + '1'
        else:
            new_name = ''.join(match[:-1]) + str(postfix_number + 1)
            return cls.suggested_username(new_name)

        return new_name

    @classmethod
    def sanitise_username(cls, name):
        return re.sub(r'\W+', '', name)

    def reset_refresh_token(self):
        self.refresh_token = uuid.uuid4().hex

    @classmethod
    def create_with_channel(cls, password=None, **kwargs):
        kwargs.setdefault('avatar', app.config['DEFAULT_AVATAR'])
        kwargs.setdefault('password_hash', '')
        user = cls(**kwargs)
        if password:
            user.set_password(password)
        user.reset_refresh_token()
        user = user.save()

        # Prevent circular import
        from rockpack.mainsite.services.video.models import Channel
        title, description, cover = app.config['FAVOURITE_CHANNEL']
        channel = Channel(
            favourite=True,
            title=title,
            description=description,
            cover=cover,
            owner=user.id,
            public=True,
        )
        channel.save()

        return user

    @classmethod
    def create_from_external_system(cls, eu, locale):
        from rockpack.mainsite.services.oauth.models import ExternalToken
        if ExternalToken.query.filter_by(external_system=eu.system, external_uid=eu.id).count():
            return None

        avatar = eu.avatar
        if avatar:
            avatar = resize_and_upload(avatar, 'AVATAR')

        new_username = cls.suggested_username(
            cls.sanitise_username(eu.username or eu.display_name))

        return cls.create_with_channel(
            username=new_username,
            first_name=eu.first_name,
            last_name=eu.last_name,
            email=eu.email,
            gender=eu.gender,
            avatar=avatar,
            date_of_birth=eu.dob,
            locale=locale,
        )

    def get_flag(self, flag):
        return flag in [f.flag for f in self.flags]

    def set_flag(self, flag):
        if not self.get_flag(flag):
            userflag = UserFlag(flag=flag)
            self.flags.append(userflag)
            return userflag

    def unset_flag(self, flag):
        UserFlag.query.filter_by(user=self.id, flag=flag).delete()


class UserFlag(db.Model):
    __tablename__ = 'user_flag'
    __table_args__ = (
        PrimaryKeyConstraint('user', 'flag'),
    )

    user = Column(ForeignKey('user.id'), nullable=False)
    flag = Column(Enum(*USER_FLAGS, name='user_flag_enum'), nullable=False)

    def get_resource_url(self, own=True):
        return url_for('userws.get_flag_item', userid=self.user, flag=self.flag)
    resource_url = property(get_resource_url)


class UserActivity(db.Model):
    __tablename__ = 'user_activity'

    id = Column(Integer, primary_key=True)
    user = Column(ForeignKey('user.id'), nullable=False)
    action = Column(String(16), nullable=False)
    date_actioned = Column(DateTime(), nullable=False, default=func.now())
    object_type = Column(String(16), nullable=False)
    object_id = Column(String(64), nullable=False)
    locale = Column(ForeignKey('locale.id'), nullable=False, server_default='')


class UserContentFeed(db.Model):
    __tablename__ = 'user_content_feed'

    id = Column(Integer, primary_key=True)
    user = Column(ForeignKey('user.id'), nullable=False)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    channel = Column(ForeignKey('channel.id'), nullable=False)
    video_instance = Column(ForeignKey('video_instance.id', ondelete='CASCADE'), nullable=True)
    stars = Column(Text())


class UserNotification(db.Model):
    __tablename__ = 'user_notification'

    id = Column(Integer, primary_key=True)
    user = Column(ForeignKey('user.id'), nullable=False)
    date_created = Column(DateTime(), nullable=False, default=func.now())
    date_read = Column(DateTime(), nullable=True)
    message_type = Column(String(16), nullable=False)
    message = Column(Text())


class UserAccountEvent(db.Model):
    __tablename__ = 'user_account_event'

    id = Column(Integer, primary_key=True)
    username = Column(String(52), nullable=False)
    event_date = Column(DateTime(), nullable=False, default=func.now())
    event_type = Column(String(32), nullable=False)
    event_value = Column(String(1024), nullable=False)
    ip_address = Column(String(32), nullable=False)
    user_agent = Column(String(1024), nullable=False)
    clientid = Column(CHAR(22), nullable=False)


class ReservedUsername(db.Model):
    __tablename__ = 'reserved_username'

    username = Column(String(52), nullable=False, primary_key=True)
    external_system = Column(Enum(*EXTERNAL_SYSTEM_NAMES, name='external_system_names'), nullable=False)
    external_uid = Column(String(1024), nullable=False)
    external_data = Column(Text())


class Subscription(db.Model):
    __tablename__ = 'subscription'
    __table_args__ = (
        PrimaryKeyConstraint('user', 'channel'),
    )

    user = Column(ForeignKey('user.id'), nullable=False)
    channel = Column(ForeignKey('channel.id'), nullable=False)
    date_created = Column(DateTime(), nullable=False, default=func.now())

    @property
    def id(self):
        return self.user + self.channel

    def get_resource_url(self, own=False):
        view = 'userws.delete_subscription_item'
        return url_for(view, userid=self.user, channelid=self.channel)
    resource_url = property(get_resource_url)


def username_exists(username):
    username_filter = lambda m: func.lower(m.username) == username.lower()
    if User.query.filter(username_filter(User)).count():
        return 'exists'
    if ReservedUsername.query.filter(username_filter(ReservedUsername)).count():
        return 'reserved'


def _es_user_insert(mapper, connection, target):
    add_user_to_index(target)


event.listen(User, 'after_insert', _es_user_insert)
event.listen(User, 'after_update', _es_user_insert)
event.listen(User, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z))
