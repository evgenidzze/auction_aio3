from typing import List

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.mysql import insert

from database.models.channel_group import ChannelGroup
from database.models.group_subscription_plan import GroupSubscriptionPlan
from database.models.user import User
from database.services.base import async_session


class UserService:
    _session = None  # змінна для зберігання сесії

    @classmethod
    async def get_session(cls):
        """Отримати сесію на рівні класу, якщо вона ще не створена."""
        if cls._session is None:
            cls._session = async_session()
        return cls._session

    @staticmethod
    async def get_user(user_id) -> User:
        """
        Отримує інформацію про користувача за його Telegram ID.

        :param user_id: Telegram ID користувача.
        :return: Об'єкт User або None, якщо запис не знайдено.
        """
        async with async_session() as session:
            stmt = select(User).where(User.telegram_id == user_id)
            res = await session.execute(stmt)
            user = res.fetchone()
            if user:
                return user[0]

    @staticmethod
    async def update_user_sql(telegram_id, **kwargs):
        """
        Оновлює інформацію про користувача на основі вхідних параметрів.

        :param telegram_id: Telegram ID користувача.
        :param kwargs: Поля, які потрібно оновити (ключ-значення).
        """
        async with async_session() as session:
            stmt = update(User).where(User.telegram_id == telegram_id).values(kwargs)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def insert_or_update_user(telegram_id, language):
        """
        Додає нового користувача або оновлює його мову в системі.

        :param telegram_id: Унікальний Telegram ID користувача.
        :param language: Мова, обрана користувачем.
        """
        async with async_session() as session:
            stmt = insert(User).values(
                telegram_id=telegram_id,
                language=language
            ).on_duplicate_key_update(
                language=language
            ).prefix_with('IGNORE')
            await session.execute(stmt)
            await session.commit()

