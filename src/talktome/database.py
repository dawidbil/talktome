from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from talktome.models.base import Base

engine: Engine = create_engine("sqlite:///database.db")
SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
