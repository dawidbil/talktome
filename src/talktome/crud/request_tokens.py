import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from talktome.models.request_tokens import RequestTokens

logger = logging.getLogger(__name__)


def add_request_tokens(db: Session, channel_id: int, tokens: int):
    db.add(RequestTokens(channel_id=channel_id, tokens=tokens, created_at=datetime.now(tz=UTC)))
    db.commit()
    logger.info(f"Added {tokens} request tokens for channel {channel_id}")


def get_request_tokens(db: Session, channel_id: int) -> list[RequestTokens]:
    return (
        db.query(RequestTokens)
        .filter(RequestTokens.channel_id == channel_id)
        .order_by(RequestTokens.created_at.desc())
        .all()
    )


def delete_request_tokens_older_than_24_hours(db: Session):
    request_tokens_to_delete = db.query(RequestTokens).filter(
        RequestTokens.created_at < datetime.now(tz=UTC) - timedelta(hours=24)
    )
    request_tokens_to_delete.delete()
    db.commit()
    logger.info(f"Deleted {request_tokens_to_delete.count()} request tokens older than 24 hours")


def delete_request_tokens(db: Session, channel_id: int):
    request_tokens_to_delete = db.query(RequestTokens).filter(
        RequestTokens.channel_id == channel_id
    )
    request_tokens_to_delete.delete()
    db.commit()
    logger.info(
        f"Deleted {request_tokens_to_delete.count()} request tokens for channel {channel_id}"
    )
