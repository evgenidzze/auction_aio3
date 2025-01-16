from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.mysql import insert

from database.models.channel_group import ChannelGroup
from database.models.group_subscription_plan import GroupSubscriptionPlan
from database.services.base import async_session


class GroupSubscriptionPlanService:
    _session = None  # змінна для зберігання сесії

    @classmethod
    async def get_session(cls):
        """Отримати сесію на рівні класу, якщо вона ще не створена."""
        if cls._session is None:
            cls._session = async_session()
        return cls._session

    @staticmethod
    async def create_subscription(chat_id, auction_sub_time,
                                  auction_paid,
                                  auction_token,
                                  ads_sub_time,
                                  ads_paid,
                                  ads_token,
                                  free_trial):
        async with await GroupSubscriptionPlanService.get_session() as session:
            stmt_subscription_plan = insert(GroupSubscriptionPlan).values(
                group_fk=chat_id,
                auction_sub_time=auction_sub_time,
                auction_paid=auction_paid,
                auction_token=auction_token,
                ads_sub_time=ads_sub_time,
                ads_paid=ads_paid,
                ads_token=ads_token,
                free_trial=free_trial
            )
            await session.execute(stmt_subscription_plan)
            await session.commit()

    @staticmethod
    async def get_subscription(group_id):
        async with async_session() as session:
            stmt = (
                select(GroupSubscriptionPlan)
                .join(GroupSubscriptionPlan.group)  # З’єднання з ChannelGroup
                .filter(ChannelGroup.chat_id == group_id)  # Використовуємо filter для умов
                .options(selectinload(GroupSubscriptionPlan.group))  # Завантаження відносин
            )
            res = await session.execute(stmt)
            chat = res.scalars().first()
            return chat

    @staticmethod
    async def update_group_subscription_sql(chat_id, **kwargs):
        """
        Оновлює інформацію про підписку у базі за group_id (Group telegram id).

        :param chat_id: Унікальний ідентифікатор чату.
        :param kwargs: Поля, які потрібно оновити (ключ-значення).
        """
        async with async_session() as session:
            stmt = update(GroupSubscriptionPlan).where(ChannelGroup.chat_id == chat_id).values(**kwargs)
            try:
                await session.execute(stmt)
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"Error updating subscription of chat {chat_id}: {e}")
                raise e
