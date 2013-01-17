from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base

from rockpack.mainsite import app

db_engine = create_engine(app.config['DATABASE_CONNECTION_STRING'])

Base = declarative_base(bind=db_engine)
Session = scoped_session(sessionmaker(db_engine))
session = Session()
