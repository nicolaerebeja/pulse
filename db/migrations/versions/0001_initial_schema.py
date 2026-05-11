"""Initial schema — chats, yt_channels, chat_subs, videos, notif_sent.

Revision ID: 0001
Revises:
Create Date: 2026-05-10
"""

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "chats",
        sa.Column("chat_id", sa.BigInteger(), primary_key=True),
        sa.Column("chat_type", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "yt_channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("yt_id", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("last_video_id", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "chat_subs",
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("chats.chat_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("yt_channel_id", sa.Integer(), sa.ForeignKey("yt_channels.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("yt_id", sa.Text(), nullable=False, unique=True),
        sa.Column("yt_channel_id", sa.Integer(), sa.ForeignKey("yt_channels.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "notif_sent",
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("chats.chat_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("video_yt_id", sa.Text(), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("notif_sent")
    op.drop_table("videos")
    op.drop_table("chat_subs")
    op.drop_table("yt_channels")
    op.drop_table("chats")
