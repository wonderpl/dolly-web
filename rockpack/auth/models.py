from sqlalchemy import (
    String,
    Column,
    Integer,
    ForeignKey,
    Enum,
)

from sqlalchemy.orm.exc import NoResultFound

from rockpack.core.dbapi import session
from rockpack.core.dbapi import Base

class InvalidUserException(Exception):
    pass


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(254))
    email = Column(String(254))

    @classmethod
    def get_from_username(cls, username):
        try:
            return session.Query(cls).get(username)
        except NoResultFound:
            raise InvalidUserException


READ = 'read'
READ_WRITE = 'read/write'
DELETE = 'delete'


class Role(Base):
    """ Role types like 'Tech', or 'Marketing' ... """
    __tablename__ = 'auth_roles'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))


class Need(Base):
    """ The need for the `role`
            e.g. `admin` needs `can_edit_post` """
    __tablename__ = 'auth_needs'

    id = Column(Integer, primary_key=True)
    group = Column(ForeignKey(Role))
    name = Column(String(40))


class AccessRights(Base):
    __tablename__ = 'auth_access_rights'

    id = Column(Integer, primary_key=True)
    group = Column(ForeignKey(Role))
    need = Column(ForeignKey(Need))
    access = Column(Enum(READ, READ_WRITE, DELETE, name='access_types'))


class UserRole(Base):
    __tablename__ = 'user_roles'

    id = Column(Integer, primary_key=True)
    role = Column(ForeignKey(Role))
