import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, Integer, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


@dataclass
class RequestTokens(Base):
    __tablename__: str = "request_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Database:
    def __init__(self):
        self.engine: Engine = create_engine("sqlite:///database.db")
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def add_request_tokens(self, channel_id: int, tokens: int):
        with self.Session() as session:
            session.add(
                RequestTokens(channel_id=channel_id, tokens=tokens, created_at=datetime.now(tz=UTC))
            )
            session.commit()

    def get_request_tokens(self, channel_id: int) -> list[RequestTokens]:
        with self.Session() as session:
            return (
                session.query(RequestTokens)
                .filter(RequestTokens.channel_id == channel_id)
                .order_by(RequestTokens.created_at.desc())
                .all()
            )

    def delete_request_tokens_older_than_24_hours(self):
        with self.Session() as session:
            request_tokens_to_delete = session.query(RequestTokens).filter(
                RequestTokens.created_at < datetime.now(tz=UTC) - timedelta(hours=24)
            )
            logger.info(
                f"Deleting {request_tokens_to_delete.count()} request tokens older than 24 hours"
            )
            request_tokens_to_delete.delete()
            session.commit()
