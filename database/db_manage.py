import datetime
from typing import List, Union, Type, Sequence

from sqlalchemy import String, Integer, Text, ForeignKey, select, update, delete, Boolean, TIMESTAMP, text, func, Index, \
    Enum
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from utils.config import DB_PASS, DB_NAME, DB_HOST, DB_USER, PORT
from enum import Enum as PyEnum

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{PORT}/{DB_NAME}"
engine = create_async_engine(url=DATABASE_URL, connect_args={"connect_timeout": 10},
                             pool_size=10,
                             max_overflow=20,
                             pool_recycle=3600)
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


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
    partner_referral_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)  # token of created referral link
    merchant_id: Mapped[str] = mapped_column(type_=String(100), nullable=True, unique=True)  # id of activated merchant

    def __repr__(self):
        return f'<User {self.telegram_id}>'


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
        new_text (str): Новий текст лота.
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


class GroupType(PyEnum):
    GROUP = 'group'
    CHANNEL = 'channel'
    SUPERGROUP = 'SUPERGROUP'


class ChannelGroup(Base):
    """
    Модель групового чату.

    Атрибути:
        id (int): Унікальний ідентифікатор чату.
        chat_name (str): Назва чату.
        owner_telegram_id (str): Telegram ID власника чату.
        chat_id (str): Унікальний ідентифікатор чату.
        chat_type (str): Тип чату (group, channel, або supergroup).
        chat_link (str): Посилання на чат.
        auction_sub_time (int): Час підписки на аукціон.
        auction_paid (bool): Прапорець оплати аукціону.
        auction_token (str): Токен аукціону.
        ads_sub_time (int): Час підписки на оголошення.
        ads_paid (bool): Прапорець оплати на оголошення.
        ads_token (str): Токен оголошення.
        free_trial (int): Час unix безкоштовної підписки.
    """
    __tablename__ = 'ChannelGroup'
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True, unique=True)
    chat_name: Mapped[str] = mapped_column(nullable=True, type_=String(255))
    owner_telegram_id: Mapped[str] = mapped_column(ForeignKey('User.telegram_id'), nullable=False)
    chat_id: Mapped[str] = mapped_column(primary_key=True, type_=String(45), nullable=False, unique=True)
    chat_type: Mapped[GroupType] = mapped_column(Enum(GroupType), nullable=False)
    # is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    chat_link: Mapped[str] = mapped_column(nullable=True, type_=String(255), default=None, server_default=None)

    # paypal_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)

    auction_sub_time: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    auction_paid: Mapped[bool] = mapped_column(type_=Boolean, default=False)
    auction_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)

    ads_sub_time: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    ads_paid: Mapped[bool] = mapped_column(type_=Boolean, default=False)
    ads_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)

    free_trial: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    def __repr__(self):
        return f'<ChannelGroup {self.id}>'


########################################################################################################################
# FUNCTIONS FOR DATABASE                                                                                               #
########################################################################################################################


async def create_group_channel(owner_telegram_id, chat_id, chat_type, chat_name, chat_link=None):
    """
    Створює або оновлює запис для групового чату чи каналу.

    :param owner_telegram_id: Telegram ID власника чату.
    :param chat_id: Унікальний ідентифікатор чату.
    :param chat_type: Тип чату (group, channel, або supergroup).
    :param chat_name: Назва чату.
    :param chat_link: Посилання на чат (опціонально).
    """
    async with async_session() as session:  # async_session має бути створений заздалегідь
        stmt = insert(ChannelGroup).values(
            owner_telegram_id=owner_telegram_id,
            chat_id=chat_id,
            chat_type=chat_type,
            chat_name=chat_name,
            chat_link=chat_link
        )
        # Додаємо ON DUPLICATE KEY UPDATE
        stmt = stmt.on_duplicate_key_update(
            chat_type=stmt.inserted.chat_type,
            chat_name=stmt.inserted.chat_name,
            chat_link=stmt.inserted.chat_link
        )
        await session.execute(stmt)
        await session.commit()


async def insert_or_update_user(telegram_id, language):
    """
    Додає нового користувача або оновлює його мову в системі.

    :param telegram_id: Унікальний Telegram ID користувача.
    :param language: Мова, обрана користувачем.
    """
    async with async_session() as session:
        new_user = User
        stmt = insert(new_user).values(
            telegram_id=telegram_id,
            language=language
        ).on_duplicate_key_update(
            language=language
        ).prefix_with('IGNORE')
        await session.execute(stmt)
        await session.commit()


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


async def update_adv_sql(adv_id, **kwargs):
    """
    Оновлює інформацію про рекламу на основі її унікального ID.

    :param adv_id: Унікальний ідентифікатор реклами.
    :param kwargs: Поля, які потрібно оновити (ключ-значення).
    """
    async with async_session() as session:
        stmt = update(Advertisement).where(Advertisement.id == adv_id).values(kwargs)
        await session.execute(stmt)
        await session.commit()


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
            photos_link=fsm_data.get('photos_link')

        )
        session.add(new_lot)
        await session.commit()
        await session.refresh(new_lot)
        return str(new_lot.id)


async def create_adv(owner_id, fsm_data):
    """
    Створює новий запис для реклами у системі.

    :param owner_id: Telegram ID власника реклами.
    :param fsm_data: Дані реклами, отримані з FSM.
    :return: ID створеної реклами у вигляді рядка.
    """
    async with async_session() as session:
        new_adv = Advertisement(
            owner_telegram_id=owner_id,
            description=fsm_data.get('description'),
            photo_id=fsm_data.get('photo_id'),
            video_id=fsm_data.get('video_id'),
            city=fsm_data.get('city'),
            photos_link=fsm_data.get('photos_link'),
            post_per_day=fsm_data.get('repost_count')
        )
        session.add(new_adv)
        await session.commit()
        await session.refresh(new_adv)
        return str(new_adv.id)


async def get_lot(lot_id) -> Lot:
    """
    Отримує дані лота з бази за його унікальним ID.

    :param lot_id: Унікальний ідентифікатор лота.
    :return: Об'єкт Lot або None, якщо запис не знайдено.
    """
    async with async_session() as session:
        stmt = select(Lot).where(Lot.id == lot_id)
        execute = await session.execute(stmt)
        res = execute.fetchone()
        if res:
            return res[0]


async def get_adv(adv_id) -> Advertisement:
    """
    Отримує дані реклами з бази за її унікальним ID.

    :param adv_id: Унікальний ідентифікатор реклами.
    :return: Об'єкт Advertisement або None, якщо запис не знайдено.
    """
    async with async_session() as session:
        stmt = select(Advertisement).where(Advertisement.id == adv_id)
        execute = await session.execute(stmt)
        res = execute.fetchone()
        if res:
            return res[0]


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


async def get_user_chats(user_id) -> List[ChannelGroup]:
    """
    Отримує всі чати, пов'язані з вказаним користувачем.

    :param user_id: Telegram ID користувача.
    :return: Список об'єктів ChannelGroup.
    """
    async with async_session() as session:
        stmt = select(ChannelGroup).where(ChannelGroup.owner_telegram_id == user_id)
        res = await session.execute(stmt)
        chats = list(res.scalars().all())
        return chats


async def get_all_chats() -> List[ChannelGroup]:
    """
    Отримує список усіх активних чатів, які мають посилання.

    :return: Список об'єктів ChannelGroup.
    """
    async with async_session() as session:
        stmt = select(ChannelGroup).where(ChannelGroup.chat_link != None)
        res = await session.execute(stmt)
        chats = res.scalars().all()
        return chats


async def get_chat_record(chat_id):
    """
    Отримує інформацію про чат із бази за його ID.

    :param chat_id: Унікальний ідентифікатор чату.
    :return: Об'єкт ChannelGroup або None, якщо запис не знайдено.
    """
    async with async_session() as session:
        stmt = select(ChannelGroup).where(ChannelGroup.chat_id == chat_id)
        res = await session.execute(stmt)
        chat = res.scalars().first()
        return chat


async def update_chat_sql(chat_id, **kwargs):
    """
    Оновлює інформацію про чат у базі за його ID.

    :param chat_id: Унікальний ідентифікатор чату.
    :param kwargs: Поля, які потрібно оновити (ключ-значення).
    """
    async with async_session() as session:
        stmt = update(ChannelGroup).where(ChannelGroup.chat_id == chat_id).values(**kwargs)
        try:
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"Error updating chat {chat_id}: {e}")
            raise e

