"""The mapped classes: Author, Post, Comment — onto topic 16's tables.

``registry(metadata=...)`` binds this mapping to the SAME ``MetaData``
the Core schema (``guide.data.db.schema``) owns, and each class claims
its table with ``__table__ = posts`` instead of redeclaring columns.
One definition of the schema serves both worlds: Alembic autogenerates
against the Core metadata (``alembic check`` enforces the agreement),
and the ORM teaches objects over it. The ``Mapped[]`` annotations type
attributes whose columns the table already carries — SQLAlchemy matches
them by name; relationships are the only NEW wiring, and their load
behavior is deliberately the DEFAULT lazy ``select`` so the loading
strategies topic 18 teaches are choices made at query time, not
surprises baked into the mapping.
"""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    registry,
    relationship,
)

from guide.data.db.schema import authors, comments, metadata, posts

orm_registry = registry(metadata=metadata)
"""The ORM's registry, bound to the Core metadata: classes map onto the
same ``Table`` objects the migration chain is diffed against."""


class Base(DeclarativeBase, AsyncAttrs):
    """Declarative base for every mapped class in the guide.

    ``AsyncAttrs`` adds the ``awaitable_attrs`` accessor every mapped
    attribute gains in async code — the async-honest way to touch a
    relationship that may still need loading (see the probe's strategy
    runs: a lazy attribute access from an async context without it is
    an error, not a pause).
    """

    registry = orm_registry


class Author(Base):
    """One guide author, mapped onto the ``authors`` table."""

    __table__ = authors

    id: Mapped[uuid.UUID]
    name: Mapped[str]
    email: Mapped[str]
    bio: Mapped[str]
    created_at: Mapped[datetime]

    posts: Mapped[list["Post"]] = relationship(back_populates="author")


class Post(Base):
    """One guide post, mapped onto the ``posts`` table.

    ``version_id_col`` turns the migration-0003 ``version`` column into
    an optimistic lock: every UPDATE the session flushes carries
    ``WHERE version = <loaded version>`` and sets the next integer, so a
    write racing a stale reader matches ZERO rows and raises
    ``StaleDataError`` instead of silently clobbering the winner.
    """

    __table__ = posts
    __mapper_args__ = {"version_id_col": posts.c.version}

    id: Mapped[int]
    author_id: Mapped[uuid.UUID]
    slug: Mapped[str]
    title: Mapped[str]
    body: Mapped[str]
    tags: Mapped[list[str]]
    status: Mapped[str]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    version: Mapped[int]

    author: Mapped["Author"] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(back_populates="post")


class Comment(Base):
    """One comment on a post, mapped onto the ``comments`` table."""

    __table__ = comments

    id: Mapped[int]
    post_id: Mapped[int]
    author: Mapped[str]
    body: Mapped[str]
    created_at: Mapped[datetime]

    post: Mapped["Post"] = relationship(back_populates="comments")
