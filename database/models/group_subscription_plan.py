from sqlalchemy import ForeignKey, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from enum import Enum as PyEnum



class GroupType(PyEnum):
    GROUP = 'group'
    CHANNEL = 'channel'
    SUPERGROUP = 'SUPERGROUP'


class GroupSubscriptionPlan(Base):
    """
    Модель підписки на групу. В одної групи - одна підписка.

    Атрибути:
        group (ChannelGroup): Об'єкт групи.
        auction_sub_time (int): Час підписки на аукціон.
        auction_paid (bool): Прапорець оплати аукціону.
        auction_token (str): Токен аукціону.
        ads_sub_time (int): Час підписки на оголошення.
        ads_paid (bool): Прапорець оплати на оголошення.
        ads_token (str): Токен оголошення.
        free_trial (int): Час unix безкоштовної підписки.
    """
    __tablename__ = 'GroupSubscriptionPlan'
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True, unique=True)

    group_fk: Mapped[str] = mapped_column(ForeignKey('ChannelGroup.chat_id', ondelete='CASCADE'))
    group: Mapped["ChannelGroup"] = relationship("ChannelGroup", back_populates="subscription_plan", uselist=False)

    auction_sub_time: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    auction_paid: Mapped[bool] = mapped_column(type_=Boolean, default=False)
    auction_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)

    ads_sub_time: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    ads_paid: Mapped[bool] = mapped_column(type_=Boolean, default=False)
    ads_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)

    free_trial: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    def __repr__(self):
        return f'<GroupSubscriptionPlan {self.id}>'