import re
import uuid
import random
from datetime import datetime
from sqlalchemy import (
    String, Column, Integer, Boolean, Date, DateTime, ForeignKey,
    Text, Enum, CHAR, PrimaryKeyConstraint, event, func, between, text)
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask import g, json
from flask.ext.sqlalchemy import models_committed
from wonder.common.sqs import background_on_sqs
from rockpack.mainsite import app, cache
from rockpack.mainsite.core.token import create_access_token
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import ImageType, add_base64_pk, resize_and_upload
from rockpack.mainsite.helpers.urls import url_for


VISIBLE_USER_FLAGS = 'facebook_autopost_star', 'facebook_autopost_add'
HIDDEN_USER_FLAGS = 'unsub1', 'unsub2', 'unsub3', 'unsub4', 'bouncing'
USER_FLAGS = HIDDEN_USER_FLAGS + VISIBLE_USER_FLAGS
EXTERNAL_SYSTEM_NAMES = 'email', 'facebook', 'twitter', 'google', 'apns', 'romeo'
GENDERS_MAP = {'m': 'male', 'f': 'female'}
GENDERS = GENDERS_MAP.keys()


class User(db.Model):
    __tablename__ = 'user'

    id = Column(CHAR(22), primary_key=True)
    username = Column(String(52), unique=True, nullable=False)
    password_hash = Column(String(70), nullable=False)
    email = Column(String(254), nullable=False)
    first_name = Column(String(32), nullable=False)
    last_name = Column(String(32), nullable=False)
    date_of_birth = Column(Date())
    avatar = Column(ImageType('AVATAR'), nullable=False)
    gender = Column(Enum(*GENDERS, name='gender_enum'), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default='true', default=True)
    subscriber_count = Column(Integer, nullable=False, server_default='0', default=0)
    refresh_token = Column(String(1024), nullable=False)
    username_updated = Column(Boolean, nullable=False, server_default='false', default=False)
    date_joined = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    display_fullname = Column(Boolean, nullable=False, server_default='true', default=True)
    profile_cover = Column(ImageType('PROFILE'))
    brand_profile_cover = Column(ImageType('BRAND_PROFILE'))
    description = Column(String(100))
    site_url = Column(String(1024))
    is_influencer = Column(Boolean, nullable=False, server_default='false', default=False)

    locale = Column(ForeignKey('locale.id'), nullable=False, server_default='')

    channels = relationship('Channel')
    flags = relationship('UserFlag', backref='users')
    activity = relationship('UserActivity', backref='actor')

    def __unicode__(self):
        return self.username

    def __repr__(self):
        return 'User(id={u.id!r}, username={u.username!r})'.format(u=self)

    @classmethod
    def get_form_choices(cls):
        return cls.query.values(cls.id, cls.username)

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

    @classmethod
    def get_display_name(cls, username, first_name, last_name, display_fullname=True):
        # XXX: Needs to be more general?
        if first_name and display_fullname:
            return (u'%s %s' % (first_name, last_name)).strip()
        else:
            return username

    @property
    def display_name(self):
        return self.get_display_name(
            self.username, self.first_name, self.last_name, self.display_fullname)

    @property
    def brand(self):
        return bool(self.brand_profile_cover)

    @property
    @cache.memoize(14400)
    def twitter_screenname(self):
        from rockpack.mainsite.services.oauth.models import ExternalToken
        meta = ExternalToken.query.filter_by(
            user=self.id, external_system='twitter').value('meta')
        if meta:
            try:
                return json.loads(meta)['screen_name']
            except (ValueError, KeyError):
                pass
        return ''   # Returning None would cause the cache to be checked again

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_profile_cover(self):
        return self.brand_profile_cover or self.profile_cover

    def get_resource_url(self, own=False):
        view = 'userws.own_user_info' if own else 'userws.user_info'
        return url_for(view, userid=self.id)
    resource_url = property(get_resource_url)

    def get_credentials(self, expires_in=None):
        if expires_in is None:
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

    @classmethod
    def suggested_username(cls, source_name):
        if not username_exists(source_name):
            return source_name

        username = cls.query.filter(
            func.lower(cls.username).like('{}%'.format(source_name.lower()))
        ).order_by("username desc").limit(1).value('username')
        match = re.findall(r"[a-zA-Z_]+|\d+", username or source_name)

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
        kwargs.setdefault('profile_cover',
                          random.choice(app.config.get('DEFAULT_PROFILE_COVERS', [None])))
        kwargs.setdefault('password_hash', '')
        user = cls(**kwargs)
        if password:
            user.set_password(password)
        user.reset_refresh_token()
        user.add()

        # Prevent circular import
        from rockpack.mainsite.services.video.models import Channel
        title, description, cover = app.config['FAVOURITE_CHANNEL']
        user.channels = [
            Channel(
                favourite=True,
                title=title,
                description=description,
                cover=cover,
                public=True,
            )
        ]
        if 'WATCH_LATER_CHANNEL' in app.config:
            title, description, cover = app.config['WATCH_LATER_CHANNEL']
            user.channels.append(Channel(
                favourite=True,
                title=title,
                description=description,
                cover=cover,
                public=False,
            ))

        return user

    @classmethod
    def create_from_external_system(cls, eu, locale):
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
            description=eu.description,
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

    def promotion_map(self):
        promos = []
        now = datetime.utcnow()
        for p in self.user_promotion:
            if p.date_start < now and p.date_end > now:
                promos.append('|'.join([str(p.locale_id), str(p.category_id), str(p.position)]))
        return promos

    @classmethod
    def subscriber_count_for_userid(cls, userid):
        from rockpack.mainsite.services.video import models
        value = Subscription.query.join(
            models.Channel,
            (models.Channel.id == Subscription.channel) &
            (models.Channel.deleted == False) &
            (models.Channel.owner == userid)
        ).with_entities(func.count(func.distinct(Subscription.user))).first()

        return value[0] if value else 0


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
    tracking_code = Column(String(128))


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
    user = Column(ForeignKey('user.id'), nullable=True)
    username = Column(String(52), nullable=False)
    event_date = Column(DateTime(), nullable=False, default=func.now())
    event_type = Column(String(32), nullable=False)
    event_value = Column(String(1024), nullable=False)
    ip_address = Column(String(32), nullable=False)
    user_agent = Column(String(1024), nullable=False)
    clientid = Column(CHAR(22), nullable=False)

    user_rel = relationship('User')


class UserInterest(db.Model):
    __tablename__ = 'user_interest'

    id = Column(Integer, primary_key=True)
    user = Column(ForeignKey('user.id'), nullable=False)
    explicit = Column(Boolean, nullable=False, server_default='false', default=False)
    category = Column(ForeignKey('category.id'), nullable=False)
    weight = Column(Integer, nullable=True)


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


class UserSubscriptionRecommendation(db.Model):
    __tablename__ = 'user_subscription_recommendation'

    id = Column(Integer, primary_key=True)
    user = Column(ForeignKey('user.id'), nullable=False)
    category = Column(ForeignKey('category.id'), nullable=False)
    priority = Column(Integer, nullable=False, default='1')
    filter = Column(String(1024))

    user_rel = relationship('User')
    category_rel = relationship('Category')

    # TODO: Refactor filter properties & methods from BroadcastMessage to base class or mixin


class BroadcastMessage(db.Model):
    __tablename__ = 'broadcast_message'

    id = Column(Integer, primary_key=True)
    label = Column(String(64), nullable=False)
    external_system = Column(Enum(*EXTERNAL_SYSTEM_NAMES, name='external_system_names'), nullable=False)
    date_created = Column(DateTime(), nullable=False, default=func.now())
    date_scheduled = Column(DateTime(), nullable=False)
    date_processed = Column(DateTime())
    message = Column(Text(), nullable=False)
    url_target = Column(String(1024))
    filter = Column(String(1024))

    _filter_patterns = (
        re.compile('(gender) is ([mf])'),
        re.compile('(locale) like (\S+)'),
        re.compile('(email) like (\S+)'),
        re.compile('(age) between (\d+) and (\d+)'),
        re.compile('(subscribed) to (\S+)'),
        re.compile('(interested) in (\S+)'),
    )

    @classmethod
    def parse_filter_string(cls, str):
        for expr in str.split(','):
            expr = expr.strip()
            match = None
            for pattern in cls._filter_patterns:
                match = pattern.search(expr)
                if match:
                    break
            if match:
                yield expr, match.group(1), match.groups()[1:]
            else:
                yield expr, None, None

    @staticmethod
    def get_target_resource_url(target):
        from rockpack.mainsite.services.video import models
        model = models.Channel if target.startswith('ch') else models.VideoInstance
        object = model.query.filter_by(id=target).first()
        if object:
            return object.resource_url

    def get_users(self):
        users = User.query.filter_by(is_active=True)

        if self.filter:
            for expr, type, values in BroadcastMessage.parse_filter_string(self.filter):
                if type == 'email':
                    users = users.filter(User.email.like('%%%s' % values))
                if type == 'locale':
                    users = users.filter(User.locale.like('%s%%' % values))
                if type == 'gender':
                    users = users.filter(User.gender == values[0])
                if type == 'age':
                    users = users.filter(between(
                        func.age(User.date_of_birth),
                        text("interval '%s years'" % values[0]),
                        text("interval '%s years'" % values[1])))
                if type == 'subscribed':
                    users = users.join(Subscription,
                                       (Subscription.user == User.id) &
                                       (Subscription.channel == values[0]))
                if type == 'interested':
                    from rockpack.mainsite.services.video.models import Category
                    users = users.\
                        join(UserInterest, UserInterest.user == User.id).\
                        join(Category, Category.id == UserInterest.category).\
                        filter((Category.name == values[0]))

        if self.external_system == 'apns':
            from rockpack.mainsite.services.oauth.models import ExternalToken
            users = users.join(
                ExternalToken,
                (ExternalToken.external_system == 'apns') &
                (ExternalToken.user == User.id)
            )

        return users


def username_exists(username):
    username_filter = lambda m: func.lower(m.username) == username.lower()
    if User.query.filter(username_filter(User)).value(func.count()):
        return 'exists'
    if ReservedUsername.query.filter(username_filter(ReservedUsername)).value(func.count()):
        return 'reserved'


@background_on_sqs
def _update_user(userid, just_registered=False):
    user = User.query.get(userid)

    if just_registered and 'AUTO_FOLLOW_USERS' in app.config:
        locales = app.config['ENABLED_LOCALES']
        locale = user.locale if user.locale in locales else locales[0]
        from .api import save_owner_activity
        for ownerid in app.config['AUTO_FOLLOW_USERS']:
            try:
                save_owner_activity(user.id, 'subscribe_all', ownerid, locale)
            except Exception:
                app.logger.warning('Unable to subscribe to %s', ownerid)

    if just_registered and not app.config.get('TESTING'):
        from rockpack.mainsite.services.oauth.models import ExternalFriend
        ExternalFriend.populate_friends(userid)


@models_committed.connect_via(app)
def on_models_committed(sender, changes):
    for obj, change in changes:
        if isinstance(obj, User):
            if change == 'insert':
                _update_user(obj.id, just_registered=True)


event.listen(User, 'before_insert', lambda m, c, t: add_base64_pk(m, c, t))
