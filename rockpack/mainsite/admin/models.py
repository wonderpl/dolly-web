from sqlalchemy import (
    String, Column, Integer, DateTime, Date, Enum, CHAR, func, PrimaryKeyConstraint)
from rockpack.mainsite.core.dbapi import db


class AdminLogRecord(db.Model):

    __tablename__ = 'admin_log'

    id = Column(Integer(), primary_key=True)
    username = Column(String(254), nullable=False)
    timestamp = Column(DateTime(), nullable=False, default=func.now())
    action = Column(String(254), nullable=False)
    model = Column(String(254), nullable=False)
    instance_id = Column(String(254), nullable=False)
    value = Column(String(254), nullable=False)


class AppDownloadRecord(db.Model):
    __tablename__ = 'app_download'
    __table_args__ = (
        PrimaryKeyConstraint('source', 'version', 'action', 'country', 'date'),
    )

    source = Column(Enum('itunes', 'playstore', name='app_download_source'), nullable=False)
    version = Column(String(16), nullable=False)
    action = Column(Enum('download', 'update', name='app_download_action'), nullable=False)
    country = Column(CHAR(2), nullable=False)
    date = Column(Date(), nullable=False)
    count = Column(Integer(), nullable=False, server_default='0')
