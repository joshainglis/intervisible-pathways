from sqlalchemy import create_engine

engine = create_engine('postgresql://wallacea:Ilovearchaeology@localhost:5432/wallacea_viewsheds', echo=True)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer
from geoalchemy2 import Geography

Base = declarative_base()
Session = sessionmaker(bind=engine)


class Network1(Base):
    __tablename__ = 'network1'
    gid = Column(Integer, primary_key=True)
    fid_vs_pol = Column(Integer)
    fid_island = Column(Integer)
    fid_isla_1 = Column(Integer)
    id = Column(Integer)
    gridcode = Column(Integer)
    geog = Column(Geography)


session = Session()

print(session.query(Network1).filter(Network1.fid_isla_1 == 1919).all())
