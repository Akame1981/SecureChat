import os
import uuid
import time
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    Float,
    Text,
    ForeignKey,
    create_engine,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import text


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "server_groups.db")

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def gen_id() -> str:
    return uuid.uuid4().hex


class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    owner_id = Column(String, nullable=False)  # creator's encryption public key hex
    is_public = Column(Boolean, default=False)
    invite_code = Column(String, unique=True, nullable=False)
    key_version = Column(Integer, default=1)
    created_at = Column(Float, default=lambda: time.time())

    channels = relationship("Channel", back_populates="group", cascade="all, delete-orphan")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String, primary_key=True)  # encryption public key hex
    role = Column(String, default="member")  # owner|admin|member
    joined_at = Column(Float, default=lambda: time.time())
    encrypted_group_key = Column(Text, nullable=True)  # base64 sealed to user
    key_version = Column(Integer, default=1)
    pending = Column(Boolean, default=False)  # for admin-approval flow

    group = relationship("Group", back_populates="members")


class Channel(Base):
    __tablename__ = "channels"
    id = Column(String, primary_key=True, default=gen_id)
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, default="text")  # text|voice|announcement
    created_at = Column(Float, default=lambda: time.time())

    group = relationship("Group", back_populates="channels")

    __table_args__ = (
        UniqueConstraint("group_id", "name", name="uq_channel_group_name"),
    )


class GroupMessage(Base):
    __tablename__ = "group_messages"
    id = Column(String, primary_key=True, default=gen_id)
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), index=True, nullable=False)
    channel_id = Column(String, ForeignKey("channels.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_id = Column(String, nullable=False)  # sender enc pub hex
    ciphertext = Column(Text, nullable=False)
    nonce = Column(Text, nullable=False)
    attachment_meta = Column(Text, nullable=True)
    key_version = Column(Integer, default=1)
    timestamp = Column(Float, default=lambda: time.time(), index=True)


class ChannelMeta(Base):
    __tablename__ = "channel_meta"
    channel_id = Column(String, ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True)
    topic = Column(Text, nullable=True)
    description = Column(Text, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)
    # Ensure older databases get the new attachment_meta column without requiring a full migration tool.
    try:
        with engine.connect() as conn:
            # Query existing columns
            res = conn.execute(text("PRAGMA table_info('group_messages')"))
            cols = [r[1] for r in res.fetchall()]
            if 'attachment_meta' not in cols:
                # Add the column in-place (SQLite supports adding a nullable column)
                conn.execute(text("ALTER TABLE group_messages ADD COLUMN attachment_meta TEXT"))
    except Exception:
        # Don't fail startup for edge case DB locks or permission issues; fallback is to recreate DB manually
        pass
