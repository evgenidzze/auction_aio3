from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from database.models.advertisement import Advertisement
from database.services.base import async_session, BaseService
from utils.config import DB_PASS, DB_NAME, DB_HOST, DB_USER, PORT


class AdvertisementService(BaseService):
    _session = None  # змінна для зберігання сесії

    @staticmethod
    async def update_adv_sql(adv_id, **kwargs):
        """
        Оновлює інформацію про рекламу на основі її унікального ID.
        """
        async with await AdvertisementService.get_session() as session:
            stmt = update(Advertisement).where(Advertisement.id == adv_id).values(kwargs)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def create_adv(owner_id, fsm_data):
        """
        Створює новий запис для реклами у системі.
        """
        async with await AdvertisementService.get_session() as session:
            new_adv = Advertisement(
                owner_telegram_id=owner_id,
                description=fsm_data.get('description'),
                photo_id=fsm_data.get('photo_id'),
                video_id=fsm_data.get('video_id'),
                city=fsm_data.get('city'),
                photos_link=fsm_data.get('photos_link'),
                post_per_day=fsm_data.get('repost_count'),
                group_id=fsm_data.get('adv_group_id')
            )
            session.add(new_adv)
            await session.commit()
            await session.refresh(new_adv)
            return str(new_adv.id)

    @staticmethod
    async def get_adv(adv_id) -> Advertisement:
        """
        Отримує дані реклами з бази за її унікальним ID.
        """
        async with await AdvertisementService.get_session() as session:
            stmt = select(Advertisement).where(Advertisement.id == adv_id)
            execute = await session.execute(stmt)
            res = execute.fetchone()
            if res:
                return res[0]

    @staticmethod
    async def get_user_ads(user_id):
        """
        Отримує всі рекламні оголошення, створені користувачем.

        :param user_id: Telegram ID користувача.
        :return: Список об'єктів Advertisement.
        """
        async with async_session() as session:
            stmt = select(Advertisement).where(Advertisement.owner_telegram_id == user_id)
            res = await session.execute(stmt)
            return res.fetchall()
