from flask import g
from sqlalchemy import String, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from rockpack.mainsite.core.dbapi import db


class InvalidAdminException(Exception):
    pass


class PKPrefixLengthError(Exception):
    pass


class AdminUser(db.Model):

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
