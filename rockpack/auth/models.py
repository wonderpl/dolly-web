from sqlalchemy import (
    String,
    Column,
    Integer,
    ForeignKey,
)

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import relationship

from rockpack.core.dbapi import session
from rockpack.core.dbapi import Base

class InvalidUserException(Exception):
    pass

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(254))
    email = Column(String(254))
    token = Column(String(254))

    userrole = relationship('UserRole', backref='users')

    def save(self):
        session.add(self)
        session.commit()

    @classmethod
    def get_from_login(cls, username):
        try:
            return session.query(cls).filter_by(username=username).one()
        except NoResultFound:
            raise InvalidUserException

    @classmethod
    def get_from_email(cls, email):
        try:
            return session.query(cls).filter_by(email=email).one()
        except NoResultFound:
            raise InvalidUserException

    @classmethod
    def get_from_token(cls, token):
        try:
            return session.query(cls).filter_by(token=token).one()
        except NoResultFound:
            raise InvalidUserException


class Role(Base):

    __tablename__ = 'auth_roles'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))

    userrole = relationship('UserRole')
    rolepermissions = relationship('RolePermissions')


class Permission(Base):
    """ Permission for an action
            e.g. name `can delete video instance` """

    __tablename__ = 'auth_permissions'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))
    rolepermission = relationship('RolePermissions')


class RolePermissions(Base):
    """ The need for the `role`
            e.g. `admin` needs `can_edit_post` """

    __tablename__ = 'auth_role_permissions'

    id = Column(Integer, primary_key=True)
    role = Column(Integer, ForeignKey('auth_roles.id'))
    permission = Column(Integer, ForeignKey('auth_permissions.id'))


class UserRole(Base):

    __tablename__ = 'user_roles'

    id = Column(Integer, primary_key=True)
    role = Column(Integer, ForeignKey('auth_roles.id'))
    user = Column(Integer, ForeignKey('users.id'))
