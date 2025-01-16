from sqlalchemy import String, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.group_subscription_plan import GroupSubscriptionPlan
from enum import Enum as PyEnum


class GroupType(PyEnum):
    GROUP = 'group'
    CHANNEL = 'channel'
    SUPERGROUP = 'SUPERGROUP'


class ChannelGroup(Base):
    """
    Модель групового чату.

    Атрибути:
        id (int): Унікальний ідентифікатор чату.
        chat_name (str): Назва чату.
        owner_telegram_id (str): Telegram ID власника чату.
        chat_id (str): Унікальний ідентифікатор чату.
        chat_type (str): Тип чату (group, channel, або supergroup).
        chat_link (str): Посилання на чат.
        auction_sub_time (int): Час підписки на аукціон.
        auction_paid (bool): Прапорець оплати аукціону.
        auction_token (str): Токен аукціону.
        ads_sub_time (int): Час підписки на оголошення.
        ads_paid (bool): Прапорець оплати на оголошення.
        ads_token (str): Токен оголошення.
        free_trial (int): Час unix безкоштовної підписки.
    """
    __tablename__ = 'ChannelGroup'
    # id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True, unique=True)
    chat_id: Mapped[str] = mapped_column(primary_key=True, type_=String(45), nullable=False, unique=True)
    chat_name: Mapped[str] = mapped_column(nullable=True, type_=String(255))
    owner_telegram_id: Mapped[str] = mapped_column(ForeignKey('User.telegram_id'), nullable=False)
    chat_type: Mapped[GroupType] = mapped_column(Enum(GroupType), nullable=False)
    chat_link: Mapped[str] = mapped_column(nullable=True, type_=String(255), default=None, server_default=None)
    subscription_plan: Mapped["GroupSubscriptionPlan"] = relationship('GroupSubscriptionPlan', uselist=False,
                                                                      back_populates='group', passive_deletes=True)

    def __repr__(self):
        return f'<ChannelGroup {self.id}>'
