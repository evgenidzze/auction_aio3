from typing import Type, Union

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from database.models.advertisement import Advertisement
from database.models.base import Base
from database.models.lot import Lot
from utils.config import DB_PASS, DB_NAME, DB_HOST, DB_USER, PORT

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{PORT}/{DB_NAME}"
engine = create_async_engine(url=DATABASE_URL, connect_args={"connect_timeout": 10},
                             pool_size=10,
                             max_overflow=20,
                             pool_recycle=3600)
async_session = async_sessionmaker(engine)


async def on_startup():
    """
    Виконує ініціалізацію бази даних під час запуску програми, створюючи всі необхідні таблиці.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def delete_record_by_id(rec_id, table: Type[Union[Lot, Advertisement]]):
    """
    Видаляє запис із бази за його ID та типом таблиці.

    :param rec_id: Унікальний ідентифікатор запису.
    :param table: Клас таблиці, з якої потрібно видалити запис.
    """
    async with async_session() as session:
        stmt = delete(table).where(table.id == rec_id)
        await session.execute(stmt)
        await session.commit()


class BaseService:
    _session = None  # змінна для зберігання сесії

    @classmethod
    async def get_session(cls):
        """Отримати сесію на рівні класу, якщо вона ще не створена."""
        if cls._session is None:
            cls._session = async_session()
        return cls._session
