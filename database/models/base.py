from aiogram.enums import ChatType
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from enum import Enum as PyEnum


class Base(AsyncAttrs, DeclarativeBase):
    pass


class GroupType(PyEnum):
    GROUP = ChatType.GROUP
    CHANNEL = ChatType.CHANNEL
    SUPERGROUP = ChatType.SUPERGROUP
