from sqlalchemy import String, ForeignKey, Integer, Text, TIMESTAMP, text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class Lot(Base):
    """
    Модель лота.

    Атрибути:
        id (int): Унікальний ідентифікатор лота.
        owner_id (int): Telegram ID власника лота.
        title (str): Назва лота.
        description (str): Опис лота.
        start_price (float): Початкова ціна лота.
        current_price (float): Поточна ціна лота.
        bid_count (int): Кількість зроблених ставок.
        created_at (datetime): Дата і час створення лота.
        updated_at (datetime): Дата і час останнього оновлення.
        approved (bool): Прапорець схвалення лота.
        photo_id (str): ID фото лота.
        video_id (str): ID відео лота.
        price_steps (str): Кроки ціни лота.
        lot_time_living (int): Час життя лота.
        bid_time (datetime): Дата і час останньої ставки.
        lot_link (str): Посилання на лот.
        message_id (str): ID повідомлення лота.
        paypal_token (str): Токен PayPal.
        currency (str): Валюта лота.
        city (str): Місто лота.
        photos_link (str): Посилання на фото лота.
        new_text (str): Новий текст лота, який очікує на підтвердження модератором.
    """
    __tablename__ = 'Lot'
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True)
    owner_telegram_id: Mapped[str] = mapped_column(String(45), ForeignKey('User.telegram_id', ondelete='CASCADE',
                                                                          onupdate='RESTRICT'), nullable=False)
    bidder_telegram_id: Mapped[str] = mapped_column(String(45), nullable=True)
    last_bid: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    photo_id: Mapped[str] = mapped_column(String(255), nullable=True)
    video_id: Mapped[str] = mapped_column(String(255), nullable=True)
    start_price: Mapped[int] = mapped_column(Integer, nullable=False)
    price_steps: Mapped[str] = mapped_column(String(255), nullable=True)
    lot_time_living: Mapped[int] = mapped_column(Integer, nullable=False)
    bid_time: Mapped[str] = mapped_column(TIMESTAMP,
                                          server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    create_time: Mapped[str] = mapped_column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    lot_link: Mapped[str] = mapped_column(String(255), nullable=True)
    message_id: Mapped[str] = mapped_column(String(45), nullable=True)
    paypal_token: Mapped[str] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(45), nullable=True)
    city: Mapped[str] = mapped_column(String(45), nullable=True)
    photos_link: Mapped[str] = mapped_column(String(255), nullable=True)
    bid_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    new_text: Mapped[str] = mapped_column(Text, nullable=True)
    group_fk: Mapped[str] = mapped_column(ForeignKey('ChannelGroup.chat_id', ondelete='CASCADE'))
    group: Mapped["ChannelGroup"] = relationship(back_populates="lot")

