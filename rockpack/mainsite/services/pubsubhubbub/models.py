from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint, func
from rockpack.mainsite.core.dbapi import db


class Subscription(db.Model):

    __tablename__ = 'push_subscription'
    __table_args__ = (
        UniqueConstraint('hub', 'topic'),
    )

    id = Column(Integer, primary_key=True)
    hub = Column(String(1024), nullable=False)
    topic = Column(String(1024), nullable=False)
    verify_token = Column(String(1024), nullable=False)
    verified = Column(Boolean(), nullable=False, default=False)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    lease_expires = Column(DateTime(), nullable=False)
