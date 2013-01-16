from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base

from rockpack import app


db_engine = create_engine('postgresql://{}:{}@{}/rockpack'.format(
    app.config['USERNAME'], app.config['PASSWORD'], app.config['DATABASE'],)
    )
Base = declarative_base(bind=db_engine)
Session = scoped_session(sessionmaker(db_engine))
session = Session()
