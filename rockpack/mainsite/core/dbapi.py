from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base

from rockpack.mainsite import app

connection_string = 'postgresql://{}:{}@{}:{}/{}'.format(
        app.config['USERNAME'], app.config['PASSWORD'], app.config['HOST'], app.config['PORT'], app.config['DATABASE'])

db_engine = create_engine(connection_string)

Base = declarative_base(bind=db_engine)
Session = scoped_session(sessionmaker(db_engine))
session = Session()
