import logging

from sqlalchemy.orm import Session

from talktome.models.channel_token_limits import ChannelTokenLimits

logger = logging.getLogger(__name__)


def get_channel_token_limit(db: Session, channel_id: int) -> int:
    channel_token_limit = (
        db.query(ChannelTokenLimits).filter(ChannelTokenLimits.channel_id == channel_id).first()
    )
    if channel_token_limit is None:
        return 0
    return channel_token_limit.limit


def set_channel_token_limit(db: Session, channel_id: int, limit: int):
    channel_token_limit = (
        db.query(ChannelTokenLimits).filter(ChannelTokenLimits.channel_id == channel_id).first()
    )
    if channel_token_limit is None:
        db.add(ChannelTokenLimits(channel_id=channel_id, limit=limit))
        db.commit()
        logger.info(f"Added channel token limit for channel {channel_id}")
    else:
        db.query(ChannelTokenLimits).filter(ChannelTokenLimits.channel_id == channel_id).update(
            {ChannelTokenLimits.limit: limit}
        )
        db.commit()
        logger.info(f"Updated channel token limit for channel {channel_id}")


def delete_channel_token_limit(db: Session, channel_id: int):
    db.query(ChannelTokenLimits).filter(ChannelTokenLimits.channel_id == channel_id).delete()
    db.commit()
    logger.info(f"Deleted channel token limit for channel {channel_id}")
