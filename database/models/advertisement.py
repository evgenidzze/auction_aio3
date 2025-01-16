from sqlalchemy import ForeignKey, Text, String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class Advertisement(Base):
    """
    Модель оголошення.

    Атрибути:
        id (int): Унікальний ідентифікатор оголошення.
        owner_telegram_id (str): Telegram ID власника оголошення.
        description (str): Опис оголошення.
        photo_id (str): ID фото оголошення.
        video_id (str): ID відео оголошення.
        approved (bool): Прапорець схвалення оголошення.
        message_id (str): ID повідомлення оголошення.
        city (str): Місто оголошення.
        photos_link (str): Посилання на фото оголошення.
        post_link (str): Посилання на пост оголошення.
        new_text (str): Новий текст оголошення.
        post_per_day (int): Кількість постів на день.
    """
    __tablename__ = 'Advertisement'
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True, unique=True)
    owner_telegram_id: Mapped[str] = mapped_column(ForeignKey('User.telegram_id'), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    photo_id: Mapped[str] = mapped_column(String(255), nullable=True)
    video_id: Mapped[str] = mapped_column(String(255), nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    message_id: Mapped[str] = mapped_column(String(45), nullable=True)
    city: Mapped[str] = mapped_column(String(45), nullable=True)
    photos_link: Mapped[str] = mapped_column(String(255), nullable=True)
    post_link: Mapped[str] = mapped_column(String(255), nullable=True)
    new_text: Mapped[str] = mapped_column(Text, nullable=True)
    post_per_day: Mapped[int] = mapped_column(Integer, nullable=True)
    group_id: Mapped[str] = mapped_column(String(45), nullable=False)
