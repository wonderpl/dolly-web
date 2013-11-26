from sqlalchemy import Column, String, Integer, DateTime, CHAR, func
from rockpack.mainsite.core.dbapi import db


class JobControl(db.Model):
    __tablename__ = 'job_control'

    job = Column(String(32), primary_key=True)
    last_run = Column(DateTime(), nullable=True)


class SessionRecord(db.Model):
    __tablename__ = 'session_record'

    id = Column(Integer, primary_key=True)
    session_date = Column(DateTime(), nullable=False, default=func.now())
    ip_address = Column(String(32), nullable=False)
    user_agent = Column(String(1024), nullable=False)
    user = Column(CHAR(22), nullable=True)
    value = Column(String(256), nullable=True)


class FeedbackRecord(db.Model):
    __tablename__ = 'feedback_record'

    id = Column(Integer, primary_key=True)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    user = Column(CHAR(22), nullable=False)
    message = Column(String(1024), nullable=False)
    score = Column(Integer, nullable=True)
