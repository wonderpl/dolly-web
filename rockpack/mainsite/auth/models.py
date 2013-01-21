from sqlalchemy import (
    String,
    Column,
    Integer,
    ForeignKey,
)

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import relationship

from rockpack.mainsite.core.dbapi import session
from rockpack.mainsite.core.dbapi import Base

class InvalidAdminException(Exception):
    pass

class Admin(Base):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True)
    username = Column(String(254))
    email = Column(String(254))
    token = Column(String(254))

    adminrole = relationship('AdminRole', backref='admins')

    def save(self):
        session.add(self)
        session.commit()

    @classmethod
    def get_from_login(cls, adminid):
        try:
            return session.query(cls).filter_by(id=adminid).one()
        except NoResultFound:
            raise InvalidAdminException

    @classmethod
    def get_from_email(cls, email):
        try:
            return session.query(cls).filter_by(email=email).one()
        except NoResultFound:
            raise InvalidAdminException

    @classmethod
    def get_from_token(cls, token):
        try:
            return session.query(cls).filter_by(token=token).one()
        except NoResultFound:
            raise InvalidAdminException


class Role(Base):

    __tablename__ = 'auth_roles'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))

    adminrole = relationship('AdminRole')
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


class AdminRole(Base):

    __tablename__ = 'admin_roles'

    id = Column(Integer, primary_key=True)
    role = Column(Integer, ForeignKey('auth_roles.id'))
    admin = Column(Integer, ForeignKey('admins.id'))
