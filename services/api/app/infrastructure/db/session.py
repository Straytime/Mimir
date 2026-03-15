from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(database_url, future=True, pool_pre_ping=True)
    return engine, sessionmaker(bind=engine, expire_on_commit=False, future=True)
