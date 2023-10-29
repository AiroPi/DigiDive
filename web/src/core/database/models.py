from __future__ import annotations

from functools import partial

from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass
from sqlalchemy.orm import mapped_column as _mapped_column

mapped_column = partial(_mapped_column, default=None)


class Base(MappedAsDataclass, AsyncAttrs, DeclarativeBase):
    pass


class Code(Base):
    __tablename__ = "code"

    value: Mapped[str] = mapped_column(primary_key=True)


class Bind(Base):
    __tablename__ = "bind"

    code: Mapped[str] = mapped_column(ForeignKey(Code.value), primary_key=True)
    user_id: Mapped[str] = mapped_column(primary_key=True)
    link: Mapped[str] = mapped_column()
