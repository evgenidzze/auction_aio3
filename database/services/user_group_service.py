from typing import List

from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.mysql import insert

from database.models.user_group import UserGroup
from database.services.base import async_session


class UserGroupService:
    _session = None  # змінна для зберігання сесії

    @classmethod
    async def get_session(cls):
        """Отримати сесію на рівні класу, якщо вона ще не створена."""
        if cls._session is None:
            cls._session = async_session()
        return cls._session

    @staticmethod
    async def get_user_groups(user_id) -> List[UserGroup]:
        """
        Отримує всі групи в яких користувач приймав участь.

        :param user_id: Telegram ID користувача.
        :return: Об'єкт User або None, якщо запис не знайдено.
        """
        async with async_session() as session:
            stmt = select(UserGroup).options(selectinload(UserGroup.user), selectinload(UserGroup.group)).where(
                UserGroup.user_id == user_id)
            res = await session.execute(stmt)
            users = res.scalars().all()
            return users

    @staticmethod
    async def create_user_group(user_id, group_id):
        async with async_session() as session:
            stmt_check = select(UserGroup).where(UserGroup.user_id == user_id, UserGroup.group_id == group_id)
            result = await session.execute(stmt_check)
            existing_record = result.scalars().first()
            if existing_record:
                return False
            else:
                stmt = insert(UserGroup).values(user_id=user_id, group_id=group_id)
                await session.execute(stmt)
                await session.commit()
                return True

    @staticmethod
    async def delete_record(user_id, group_id):
        async with async_session() as session:
            stmt = delete(UserGroup).where(UserGroup.user_id == user_id, UserGroup.group_id == group_id)
            await session.execute(stmt)
            await session.commit()