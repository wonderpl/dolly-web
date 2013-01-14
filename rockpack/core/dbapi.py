from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base


db_engine = create_engine('mysql://root:pass@localhost/rockpack')
Base = declarative_base(bind=db_engine)
Session = scoped_session(sessionmaker(db_engine))
session = Session()
