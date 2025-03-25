from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class UserGroup(Base):
    """
    Модель груп аукціонами/оголошеннями яких користується юзер.
    """
    __tablename__ = 'UserGroup'
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('User.telegram_id', ondelete='CASCADE'), nullable=False)  # ForeignKey to User
    group_id: Mapped[int] = mapped_column(ForeignKey('ChannelGroup.chat_id', ondelete='CASCADE'),
                                          nullable=False)  # ForeignKey to ChannelGroup

    user: Mapped["User"] = relationship('User', back_populates='groups')  # Bi-directional relationship
    group: Mapped["ChannelGroup"] = relationship('ChannelGroup',
                                                 back_populates='users')  # Bi-directional relationship
    is_blocked: Mapped[bool] = mapped_column(nullable=False, default=False)
    advert_subscribe_time: Mapped[int] = mapped_column(nullable=False, default='0')
    auction_subscribe_time: Mapped[int] = mapped_column(nullable=False, default='0')
    user_adv_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)
    user_auction_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)


def __repr__(self):
    return f'<User {self.user_id} Group {self.group_id}>;'
