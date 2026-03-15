# models/db.py
from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional
from datetime import datetime
import os

engine = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///./serlok.db"),
    echo=False
)

class User(SQLModel, table=True):
    id:           Optional[int] = Field(default=None, primary_key=True)
    email:        str           = Field(unique=True, index=True)
    username:     str           = Field(unique=True, index=True)
    password_hash: str
    avatar_color: str           = Field(default="#10b981")
    is_online:    bool          = Field(default=False)
    share_location: bool        = Field(default=True)
    created_at:   datetime      = Field(default_factory=datetime.utcnow)
    last_seen:    datetime      = Field(default_factory=datetime.utcnow)


class Friendship(SQLModel, table=True):
    id:         Optional[int] = Field(default=None, primary_key=True)
    user_id:    int           = Field(foreign_key="user.id", index=True)
    friend_id:  int           = Field(foreign_key="user.id", index=True)
    status:     str           = Field(default="pending")  # pending, accepted, blocked
    created_at: datetime      = Field(default_factory=datetime.utcnow)


class Group(SQLModel, table=True):
    id:         Optional[int] = Field(default=None, primary_key=True)
    name:       str
    owner_id:   int           = Field(foreign_key="user.id")
    invite_code: str          = Field(unique=True, index=True)
    created_at: datetime      = Field(default_factory=datetime.utcnow)


class GroupMember(SQLModel, table=True):
    id:         Optional[int] = Field(default=None, primary_key=True)
    group_id:   int           = Field(foreign_key="group.id", index=True)
    user_id:    int           = Field(foreign_key="user.id", index=True)
    joined_at:  datetime      = Field(default_factory=datetime.utcnow)


class LocationLog(SQLModel, table=True):
    id:         Optional[int] = Field(default=None, primary_key=True)
    user_id:    int           = Field(foreign_key="user.id", index=True)
    lat:        float
    lng:        float
    accuracy:   Optional[float] = None
    recorded_at: datetime     = Field(default_factory=datetime.utcnow)


def create_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as s:
        yield s
