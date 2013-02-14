from flask import g
from werkzeug.security import (
        generate_password_hash,
        check_password_hash)


from sqlalchemy import (
    String,
    Column,
    Integer,
    ForeignKey,
    Boolean,
    event,
    CHAR,
    DateTime,
    func,
    Text,
)

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import relationship

from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import ImageType, add_base64_pk


class InvalidAdminException(Exception):
    pass


class PKPrefixLengthError(Exception):
    pass


class User(db.Model):
    __tablename__ = 'user'

    id = Column(CHAR(22), primary_key=True)
    username = Column(String(254), unique=True, nullable=False)
    # TODO: maybe generate a default password for rockpack accounts
    # and possibly for any third-party api logins.
    # nullable=True for now
    password_hash = Column(String(60), nullable=True)
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
        try:
            return g.session.query(cls).filter_by(username=str(username)).one()
        except NoResultFound:
            return None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.save()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


event.listen(User, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z))


class Admin(db.Model):
    __tablename__ = 'adminuser'

    id = Column(Integer, primary_key=True)
    username = Column(String(254))
    email = Column(String(254))
    token = Column(String(254))

    adminrole = relationship('AdminRole', backref='users')

    # TODO: maybe change these to `get_from(col, val)`

    @classmethod
    def get_from_login(cls, adminid):
        try:
            return g.session.query(cls).filter_by(id=adminid).one()
        except NoResultFound:
            raise InvalidAdminException

    @classmethod
    def get_from_email(cls, email):
        try:
            return g.session.query(cls).filter_by(email=email).one()
        except NoResultFound:
            raise InvalidAdminException

    @classmethod
    def get_from_token(cls, token):
        try:
            return g.session.query(cls).filter_by(token=token).one()
        except NoResultFound:
            raise InvalidAdminException


class OAuthToken(db.Model):
    __tablename__ = 'oauth_token'

    id = Column(Integer, primary_key=True)
    key = Column(String(254), nullable=False)
    expires = Column(DateTime(timezone=True), nullable=True, default=func.now())
    data = Column(Text, nullable=True)


class Role(db.Model):

    __tablename__ = 'auth_role'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))

    adminrole = relationship('AdminRole')
    rolepermissions = relationship('RolePermissions')


class Permission(db.Model):
    """ Permission for an action
            e.g. name `can delete video instance` """

    __tablename__ = 'auth_permission'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))
    rolepermission = relationship('RolePermissions')


class RolePermissions(db.Model):
    """ The need for the `role`
            e.g. `admin` needs `can_edit_post` """

    __tablename__ = 'auth_role_permissions'

    id = Column(Integer, primary_key=True)
    role = Column(Integer, ForeignKey('auth_role.id'))
    permission = Column(Integer, ForeignKey('auth_permission.id'))


class AdminRole(db.Model):

    __tablename__ = 'admin_role'

    id = Column(Integer, primary_key=True)
    role = Column(Integer, ForeignKey('auth_role.id'))
    admin = Column(Integer, ForeignKey('adminuser.id'))
