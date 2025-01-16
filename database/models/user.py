import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class User(Base):
    """
    Модель користувача.

    Атрибути:
        telegram_id (int): Унікальний Telegram ID користувача.
        language (str): Мова інтерфейсу, обрана користувачем.
        created_at (datetime): Дата і час створення запису.
        updated_at (datetime): Дата і час останнього оновлення запису.
        is_blocked (bool): Прапорець блокування користувача.
        reserve_time_minute (datetime.time): Час резерву лота.
        anti_sniper (datetime.time): Час антиснайпера.
        advert_subscribe_time (int): Час життя платіжного токену.
        user_adv_token (str): Токен користувача оплати.
        partner_referral_token (str): Токен реферального посилання.
        merchant_id (str): ID активованого мерчанта.
    """
    __tablename__ = 'User'
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True)
    telegram_id: Mapped[str] = mapped_column(primary_key=True, type_=String(45), nullable=False, unique=True)
    language: Mapped[str] = mapped_column(String(45), nullable=False)
    is_blocked: Mapped[bool] = mapped_column(nullable=False, default=False)
    reserve_time_minute: Mapped[datetime.time] = mapped_column(nullable=False,
                                                               default=datetime.time(hour=0, minute=10, second=0))
    anti_sniper: Mapped[datetime.time] = mapped_column(nullable=False,
                                                       default=datetime.time(hour=0, minute=10, second=0))
    advert_subscribe_time: Mapped[int] = mapped_column(nullable=False, default='0')
    user_adv_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)
    partner_referral_token: Mapped[str] = mapped_column(type_=String(255), nullable=True,
                                                        unique=True)  # token of created referral link
    merchant_id: Mapped[str] = mapped_column(type_=String(100), nullable=True, unique=True)  # id of activated merchant

    def __repr__(self):
        return f'<User {self.telegram_id}>'
