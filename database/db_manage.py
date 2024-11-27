import datetime
from typing import List, Union, Type, Sequence

from sqlalchemy import String, Integer, Text, ForeignKey, select, update, delete, Boolean, TIMESTAMP, text, func, Index, Enum
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

    is_admin: Mapped[bool] = mapped_column(nullable=False, default=False)

    def __repr__(self):
        return f'<User {self.telegram_id}>'


# class Question(Base):
#     __tablename__ = 'Question'
#     id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, autoincrement=True)
#     question: Mapped[str] = mapped_column(String(255), nullable=False)
#     sender_id: Mapped[str] = mapped_column(String(45), nullable=False)
#     lot_id: Mapped[int] = mapped_column(Integer, ForeignKey('Lot.id', ondelete='CASCADE', onupdate='RESTRICT'),
#                                         nullable=False)
#     recipient_id: Mapped[str] = mapped_column(String(45), nullable=False)
#
#     __table_args__ = (
#         Index('lot_idx', lot_id, unique=False),
#     )


# class Answer(Base):
#     __tablename__ = 'Answer'
#
#     id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, autoincrement=True)
#     answer: Mapped[str] = mapped_column(String(255), nullable=False)
#     sender_id: Mapped[str] = mapped_column(String(45), nullable=False)
#     recipient_id: Mapped[str] = mapped_column(String(45), nullable=False)
#     lot_id: Mapped[int] = mapped_column(Integer, ForeignKey('Lot.id', ondelete='CASCADE', onupdate='RESTRICT'),
#                                         nullable=False)
#
#     __table_args__ = (
#         Index('fk_Answer_1_idx', 'lot_id'),
#     )


class Lot(Base):
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
    __tablename__ = 'ChannelGroup'
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True, unique=True)
    chat_name: Mapped[str] = mapped_column(nullable=True, type_=String(255))
    owner_telegram_id: Mapped[str] = mapped_column(ForeignKey('User.telegram_id'), nullable=False)
    chat_id: Mapped[str] = mapped_column(primary_key=True, type_=String(45), nullable=False, unique=True)
    chat_type: Mapped[GroupType] = mapped_column(Enum(GroupType), nullable=False)
    # is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    chat_link: Mapped[str] = mapped_column(nullable=True, type_=String(255), default=None, server_default=None)

    # paypal_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)

    auction_sub_time: Mapped[bool] = mapped_column(nullable=False, default='0')
    auction_paid: Mapped[bool] = mapped_column(type_=Boolean, default=False)
    auction_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)

    ads_sub_time: Mapped[bool] = mapped_column(nullable=False, default='0')
    ads_paid: Mapped[bool] = mapped_column(type_=Boolean, default=False)
    ads_token: Mapped[str] = mapped_column(type_=String(255), nullable=True, unique=True)


    def __repr__(self):
        return f'<ChannelGroup {self.id}>'


async def create_group_channel(owner_telegram_id, chat_id, chat_type, chat_name, chat_link=None):
    async with async_session() as session:
        new_chat = ChannelGroup
        stmt = insert(new_chat).values(
            owner_telegram_id=owner_telegram_id,
            chat_id=chat_id,
            chat_type=chat_type,
            chat_name=chat_name,
            chat_link=chat_link
        ).on_duplicate_key_update(
            chat_id=chat_id,
            chat_type=chat_type,
            chat_name=chat_name,
            chat_link=chat_link).prefix_with('IGNORE')
        await session.execute(stmt)
        await session.commit()
        await session.close()


async def insert_or_update_user(telegram_id, language):
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
        await session.close()


async def update_user_sql(telegram_id, **kwargs):
    async with async_session() as session:
        stmt = update(User).where(User.telegram_id == telegram_id).values(kwargs)
        await session.execute(stmt)
        await session.commit()
        await session.close()


async def update_lot_sql(lot_id, **kwargs):
    async with async_session() as session:
        stmt = update(Lot).where(Lot.id == lot_id).values(kwargs)
        await session.execute(stmt)
        await session.commit()
        await session.close()


async def update_adv_sql(adv_id, **kwargs):
    async with async_session() as session:
        stmt = update(Advertisement).where(Advertisement.id == adv_id).values(kwargs)
        await session.execute(stmt)
        await session.commit()
        await session.close()


async def create_lot(fsm_data, owner_id):
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
        await session.close()
        return str(new_lot.id)


async def create_adv(owner_id, fsm_data):
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
        await session.close()
        return str(new_adv.id)


async def get_lot(lot_id) -> Lot:
    async with async_session() as session:
        stmt = select(Lot).where(Lot.id == lot_id)
        execute = await session.execute(stmt)
        res = execute.fetchone()
        if res:
            return res[0]


async def get_adv(adv_id) -> Advertisement:
    async with async_session() as session:
        stmt = select(Advertisement).where(Advertisement.id == adv_id)
        execute = await session.execute(stmt)
        res = execute.fetchone()
        if res:
            return res[0]


async def get_user_ads(user_id):
    async with async_session() as session:
        stmt = select(Advertisement).where(Advertisement.owner_telegram_id == user_id)
        res = await session.execute(stmt)
        return res.fetchall()


async def get_user_lots(user_id):
    async with async_session() as session:
        stmt = select(Lot).where(Lot.owner_telegram_id == user_id)
        res = await session.execute(stmt)
        return res.fetchall()


async def make_bid_sql(lot_id, price, bidder_id, bid_count):
    async with async_session() as session:
        stmt = update(Lot).where(Lot.id == lot_id).values(last_bid=price, bidder_telegram_id=bidder_id,
                                                          bid_count=bid_count + 1)
        await session.execute(stmt)
        await session.commit()
        await session.close()


async def get_last_bid(lot_id):
    async with async_session() as session:
        stmt = select(Lot).where(Lot.id == lot_id)
        res = await session.execute(stmt)
        return res.fetchone()[0]


async def get_user(user_id) -> User:
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == user_id)
        res = await session.execute(stmt)
        user = res.fetchone()
        if user:
            return user[0]


# async def create_question(question, sender_id, lot_id, owner_id):
#     async with async_session() as session:
#         new_question = Question(
#             question=question,
#             sender_id=sender_id,
#             lot_id=lot_id,
#             recipient_id=owner_id
#         )
#         session.add(new_question)
#         await session.commit()
#         await session.refresh(new_question)
#         await session.close()
#         return str(new_question.id)


# async def create_answer(answer, sender_id, lot_id, recipient_id):
#     async with async_session() as session:
#         new_question = Answer(
#             answer=answer,
#             sender_id=sender_id,
#             lot_id=lot_id,
#             recipient_id=recipient_id,
#         )
#         session.add(new_question)
#         await session.commit()
#         await session.refresh(new_question)
#         await session.close()
#         return str(new_question.id)


# async def get_question(question_id):
#     async with async_session() as session:
#         stmt = select(Question).where(Question.id == question_id)
#         res = await session.execute(stmt)
#         question = res.scalars().first()
#         return question


# async def get_question_or_answer(recipient_id, model_name: str):
#     model = Answer if model_name == 'answer' else Question
#     async with async_session() as session:
#         stmt = select(model).where(model.recipient_id == recipient_id)
#         res = await session.execute(stmt)
#         res = res.scalars().all()
#         return res


# async def get_answer(answer_id):
#     async with async_session() as session:
#         stmt = select(Answer).where(Answer.id == answer_id)
#         res = await session.execute(stmt)
#         answer = res.scalars().first()
#         return answer


async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# async def messages_count(owner_id, mess_type):
#     async with async_session() as session:
#         if mess_type == 'answer':
#             model = Answer
#         elif mess_type == 'question':
#             model = Question
#         stmt = select(func.count("*")).select_from(model).where(model.recipient_id == owner_id)
#
#         res = await session.execute(stmt)
#         return res.scalars().all()[0]


async def delete_record_by_id(rec_id, table: Type[Union[Lot, Advertisement]]):
    async with async_session() as session:
        stmt = delete(table).where(table.id == rec_id)
        await session.execute(stmt)
        await session.commit()
        await session.close()


async def get_user_chats(user_id) -> List[ChannelGroup]:
    async with async_session() as session:
        stmt = select(ChannelGroup).where(ChannelGroup.owner_telegram_id == user_id)
        res = await session.execute(stmt)
        chats = list(res.scalars().all())
        return chats


async def get_all_chats() -> List[ChannelGroup]:
    async with async_session() as session:
        stmt = select(ChannelGroup).where(ChannelGroup.chat_link != None)
        res = await session.execute(stmt)
        chats = res.scalars().all()
        return chats


async def get_chat_record(chat_id):
    async with async_session() as session:
        stmt = select(ChannelGroup).where(ChannelGroup.chat_id == chat_id)
        res = await session.execute(stmt)
        chat = res.scalars().first()
        return chat


async def update_chat_sql(chat_id, **kwargs):
    async with async_session() as session:
        stmt = update(ChannelGroup).where(ChannelGroup.chat_id == chat_id).values(kwargs)
        await session.execute(stmt)
        await session.commit()
        await session.close()
