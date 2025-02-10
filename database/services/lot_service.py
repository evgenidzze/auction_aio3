from sqlalchemy import select, update
from database.models.lot import Lot
from database.services.base import async_session
from sqlalchemy.orm import selectinload

class LotService:
    _session = None  # змінна для зберігання сесії

    @classmethod
    async def get_session(cls):
        """Отримати сесію на рівні класу, якщо вона ще не створена."""
        if cls._session is None:
            cls._session = async_session()
        return cls._session

    @staticmethod
    async def get_last_bid(lot_id):
        """
        Отримує останню зроблену ставку на вказаний лот.

        :param lot_id: Унікальний ідентифікатор лота.
        :return: Об'єкт Lot з останньою ставкою.
        """
        async with async_session() as session:
            stmt = select(Lot).where(Lot.id == lot_id)
            res = await session.execute(stmt)
            return res.fetchone()[0]
    @staticmethod
    async def make_bid_sql(lot_id, price, bidder_id, bid_count):
        """
        Оновлює ставку на лот із зазначенням нової ціни, користувача, що зробив ставку, та кількості ставок.

        :param lot_id: Унікальний ідентифікатор лота.
        :param price: Нова ціна ставки.
        :param bidder_id: Telegram ID користувача, що зробив ставку.
        :param bid_count: Поточна кількість ставок на лот.
        """
        async with async_session() as session:
            stmt = update(Lot).where(Lot.id == lot_id).values(last_bid=price, bidder_telegram_id=bidder_id,
                                                              bid_count=bid_count + 1)
            await session.execute(stmt)
            await session.commit()
    @staticmethod
    async def get_user_lots(user_id):
        """
        Отримує всі лоти, створені користувачем.

        :param user_id: Telegram ID користувача.
        :return: Список об'єктів Lot.
        """
        async with async_session() as session:
            stmt = select(Lot).where(Lot.owner_telegram_id == user_id)
            res = await session.execute(stmt)
            return res.fetchall()
    @staticmethod
    async def get_lot(lot_id) -> Lot:
        """
        Отримує дані лота з бази за його унікальним ID.

        :param lot_id: Унікальний ідентифікатор лота.
        :return: Об'єкт Lot або None, якщо запис не знайдено.
        """
        async with async_session() as session:
            stmt = select(Lot).options(selectinload(Lot.group)).where(Lot.id == lot_id)
            execute = await session.execute(stmt)
            res = execute.fetchone()
            if res:
                return res[0]

    @staticmethod
    async def create_lot(fsm_data, owner_id):
        """
        Створює новий запис для лота у системі.

        :param fsm_data: Дані лота, отримані з FSM (Finite State Machine).
        :param owner_id: Telegram ID власника лота.
        :return: ID створеного лота у вигляді рядка.
        """
        async with async_session() as session:
            new_lot = Lot(
                owner_telegram_id=owner_id,
                description=fsm_data.get('description'),
                start_price=fsm_data.get('price'),
                lot_time_living=fsm_data.get('lot_time_living'),
                photo_id=fsm_data.get('photo_id'),
                video_id=fsm_data.get('video_id'),
                price_steps=fsm_data.get('price_steps'),
                currency=fsm_data.get('currency'),
                city=fsm_data.get('city'),
                last_bid=fsm_data.get('price'),
                photos_link=fsm_data.get('photos_link'),
                group_fk=fsm_data.get('lot_group_id')

            )
            session.add(new_lot)
            await session.commit()
            await session.refresh(new_lot)
            return str(new_lot.id)

    @staticmethod
    async def update_lot_sql(lot_id, **kwargs):
        """
        Оновлює дані лота на основі його унікального ID.

        :param lot_id: Унікальний ідентифікатор лота.
        :param kwargs: Поля, які потрібно оновити (ключ-значення).
        """
        async with async_session() as session:
            stmt = update(Lot).where(Lot.id == lot_id).values(kwargs)
            await session.execute(stmt)
            await session.commit()