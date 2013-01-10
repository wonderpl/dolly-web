from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

db_engine = create_engine('mysql://root:pass@localhost/rockpack')

Session = scoped_session(sessionmaker(bind=db_engine))
session = Session()
