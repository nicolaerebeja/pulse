"""SQLAlchemy models — used only by Alembic for schema autogeneration. Do not use in queries."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # private / group / supergroup
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class YtChannel(Base):
    __tablename__ = "yt_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    yt_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)   # UC... channel ID
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_video_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatSub(Base):
    """A chat (private or group) is subscribed to a YouTube channel."""
    __tablename__ = "chat_subs"

    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.chat_id", ondelete="CASCADE"), primary_key=True)
    yt_channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("yt_channels.id", ondelete="CASCADE"), primary_key=True)


class Video(Base):
    """A processed YouTube video — shared across all chats that follow the channel."""
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    yt_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    yt_channel_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("yt_channels.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class NotifSent(Base):
    """Deduplication: tracks which videos were already sent to which chat."""
    __tablename__ = "notif_sent"

    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.chat_id", ondelete="CASCADE"), primary_key=True)
    video_yt_id: Mapped[str] = mapped_column(Text, primary_key=True)
