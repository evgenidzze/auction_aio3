"""
Сервіс для перевірки закінчення підписок на групи.
"""
import logging

# TODO: Можна як сервіс, а можна включити в основний файл бота або через subprocess або ще варіанти.
#  Якщо саме так залишити то в докер контейнери включити запуск.

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from datetime import datetime
from utils.config import BOT_TOKEN
from database.db_manage import ChannelGroup, engine
from keyboards.admin_kb import create_subscription_group_buttons_kb
from aiogram import Bot
from aiogram.utils.i18n import I18n
from pathlib import Path

# Ініціалізуємо локалізацію
_ = I18n(path=Path(__file__).parent.parent / 'locales', domain='auction').gettext


# --- Конфігурація ---
BATCH_SIZE = 500  # Розмір батчу
CHECK_INTERVAL_SECONDS = 300  # Інтервал перевірки (секунди)

# Ініціалізуємо бота
bot = Bot(token=BOT_TOKEN, validate_token=False)


async def send_end_subscription_message(owner_id: str, chat_id: str, group_title: str, type_subscription: str):
    """
    Відправляє повідомлення про закінчення підписки на групу.
    """
    message = {
        "auction": [
            _("Підписка на аукціон закінчилася"),
            _("Роботу аукціону було призупинено на невизначений час, всі дані збережено. Для поновлення роботи зверніться до адміністратора бота."),
        ],
        "ads": [
            _("Підписка на оголошення закінчилася"),
            _("Роботу оголошень було призупинено на невизначений час, всі дані збережено. Для поновлення роботи зверніться до адміністратора бота."),
        ],
    }[type_subscription]

    # to owner
    await bot.send_message(owner_id, f"{message[0]} '{group_title}'", reply_markup=create_subscription_group_buttons_kb(chat_id))
    # to groups
    await bot.send_message(chat_id, message[1])


async def process_expired_flags(session: AsyncSession):
    """
    Проходить по групах, у яких закінчився час `auction_time` або `ads_time`,
    оновлює відповідні флажки та повертає список груп для подальшого використання.
    """
    current_timestamp = datetime.utcnow().timestamp()

    # Вибираємо групи, у яких закінчився auction_time або ads_time
    query = (
        select(ChannelGroup)
        .where(
            (ChannelGroup.auction_sub_time < current_timestamp) & ChannelGroup.auction_paid.is_(True) |
            (ChannelGroup.ads_sub_time < current_timestamp) & ChannelGroup.ads_paid.is_(True)
        )
        .limit(BATCH_SIZE)
    )

    # Отримуємо групи батчами
    result = await session.execute(query)
    groups = result.scalars().all()

    # Якщо немає груп, виходимо
    if not groups:
        return []

    # Оновлюємо флажки для груп
    for i, group in enumerate(groups):
        if group.auction_sub_time < current_timestamp and group.auction_paid:
            group.auction_paid = False
            await send_end_subscription_message(group.owner_telegram_id, group.chat_id, group.chat_name, "auction")
        if group.ads_sub_time < current_timestamp and group.ads_paid:
            group.ads_paid = False
            await send_end_subscription_message(group.owner_telegram_id, group.chat_id, group.chat_name, "ads")

    # Зберігаємо зміни
    await session.commit()

    return groups


async def main():
    """
    Основний цикл перевірки груп і оновлення флажків.
    """
    while True:
        try:
            # Створюємо нову сесію на кожну ітерацію
            async with async_sessionmaker(engine, class_=AsyncSession)() as session:
                expired_groups = await process_expired_flags(session)

                # Чекаємо перед наступною перевіркою
                if not expired_groups:
                    logging.info("No expired groups found. Sleeping...")
        except Exception as e:
            logging.exception(f"Error during processing: {e}")
        finally:
            # Завжди чекаємо перед наступною ітерацією
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
