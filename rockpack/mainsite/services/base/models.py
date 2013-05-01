from sqlalchemy import Column, String, DateTime
from rockpack.mainsite.core.dbapi import db


class JobControl(db.Model):
    __tablename__ = 'job_control'

    job = Column(String(32), primary_key=True)
    last_run = Column(DateTime(), nullable=True)
