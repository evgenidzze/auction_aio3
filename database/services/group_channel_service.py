from typing import List

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.mysql import insert

from database.models.channel_group import ChannelGroup
from database.services.base import async_session
from database.services.group_subscription_plan_service import GroupSubscriptionPlanService


class GroupChannelService:
    _session = None  # змінна для зберігання сесії

    @classmethod
    async def get_session(cls):
        """Отримати сесію на рівні класу, якщо вона ще не створена."""
        if cls._session is None:
            cls._session = async_session()
        return cls._session

    @staticmethod
    async def get_group_record(chat_id):
        """
        Отримує інформацію про чат із бази за його ID.

        :param chat_id: Унікальний ідентифікатор чату.
        :return: Об'єкт ChannelGroup або None, якщо запис не знайдено.
        """
        async with async_session() as session:
            stmt = select(ChannelGroup).options(selectinload(ChannelGroup.subscription_plan)).where(
                ChannelGroup.chat_id == chat_id)
            res = await session.execute(stmt)
            chat = res.scalars().first()
            return chat

    @staticmethod
    async def get_all_groups() -> List[ChannelGroup]:
        """
        Отримує список усіх активних чатів, які мають посилання.

        :return: Список об'єктів ChannelGroup.
        """
        async with async_session() as session:
            stmt = select(ChannelGroup).where(ChannelGroup.chat_link != None)
            res = await session.execute(stmt)
            chats = res.scalars().all()
            return chats

    @staticmethod
    async def get_group_by_owner_telegram_id(user_id) -> List[ChannelGroup]:
        """
        Отримує всі чати, пов'язані з вказаним власником.

        :param user_id: Telegram ID користувача.
        :return: Список об'єктів ChannelGroup.
        """
        async with async_session() as session:
            stmt = select(ChannelGroup).where(ChannelGroup.owner_telegram_id == user_id)
            res = await session.execute(stmt)
            chats = list(res.scalars().all())
            return chats

    @staticmethod
    async def create_group(owner_telegram_id, chat_id, chat_type, chat_name, chat_link=None):
        """
        Створює або оновлює запис для групового чату чи каналу.

        :param owner_telegram_id: Telegram ID власника чату.
        :param chat_id: Унікальний ідентифікатор чату.
        :param chat_type: Тип чату (group, channel, або supergroup).
        :param chat_name: Назва чату.
        :param chat_link: Посилання на чат (опціонально).
        """
        async with async_session() as session:
            new_group = insert(ChannelGroup).values(
                owner_telegram_id=owner_telegram_id,
                chat_id=chat_id,
                chat_type=chat_type,
                chat_name=chat_name,
                chat_link=chat_link
            )
            # Додаємо ON DUPLICATE KEY UPDATE
            new_group = new_group.on_duplicate_key_update(
                chat_type=new_group.inserted.chat_type,
                chat_name=new_group.inserted.chat_name,
                chat_link=new_group.inserted.chat_link
            )
            await session.execute(new_group)
            await session.commit()

            # додаємо запис тарифу у GroupSubscriptionPlan
            await GroupSubscriptionPlanService.create_subscription(chat_id=chat_id, auction_sub_time=0,
                                                                   auction_paid=False,
                                                                   auction_token=None,
                                                                   ads_sub_time=0,
                                                                   ads_paid=False,
                                                                   ads_token=None,
                                                                   free_trial=0)

    @staticmethod
    async def update_chat_sql(chat_id, **kwargs):
        async with async_session() as session:
            stmt = update(ChannelGroup).where(ChannelGroup.chat_id == chat_id).values(kwargs)
            await session.execute(stmt)
            await session.commit()
            await session.close()