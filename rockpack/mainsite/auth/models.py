from flask import g

from sqlalchemy import (
    String,
    Column,
    Integer,
    ForeignKey,
    Boolean,
    event,
)

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import relationship

from rockpack.mainsite.core.dbapi import Base
from rockpack.mainsite.helpers.db import ImageType, add_base64_pk


class InvalidAdminException(Exception):
    pass


class PKPrefixLengthError(Exception):
    pass


class User(Base):
    __tablename__ = 'user'

    id = Column(String(24), primary_key=True)
    username = Column(String(254), unique=True, nullable=False)
    email = Column(String(254), nullable=False)
    first_name = Column(String(254), nullable=False)
    last_name = Column(String(254), nullable=False)
    avatar = Column(ImageType('AVATAR'), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

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


class Admin(Base):
    __tablename__ = 'adminuser'

    id = Column(Integer, primary_key=True)
    username = Column(String(254))
    email = Column(String(254))
    token = Column(String(254))

    adminrole = relationship('AdminRole', backref='users')

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


class Role(Base):

    __tablename__ = 'auth_role'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))

    adminrole = relationship('AdminRole')
    rolepermissions = relationship('RolePermissions')


class Permission(Base):
    """ Permission for an action
            e.g. name `can delete video instance` """

    __tablename__ = 'auth_permission'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))
    rolepermission = relationship('RolePermissions')


class RolePermissions(Base):
    """ The need for the `role`
            e.g. `admin` needs `can_edit_post` """

    __tablename__ = 'auth_role_permissions'

    id = Column(Integer, primary_key=True)
    role = Column(Integer, ForeignKey('auth_role.id'))
    permission = Column(Integer, ForeignKey('auth_permission.id'))


class AdminRole(Base):

    __tablename__ = 'admin_role'

    id = Column(Integer, primary_key=True)
    role = Column(Integer, ForeignKey('auth_role.id'))
    admin = Column(Integer, ForeignKey('adminuser.id'))
