"""
Сервіс для перевірки закінчення підписок на групи.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from datetime import datetime
from sqlalchemy.orm import selectinload

from database.services.base import engine
from database.services.group_subscription_plan_service import GroupSubscriptionPlanService
from utils.config import BOT_TOKEN, DEV_ID
from database.models.group_subscription_plan import GroupSubscriptionPlan
from keyboards.admin_kb import activate_ad_auction_kb
from aiogram import Bot
from aiogram.utils.i18n import I18n
from pathlib import Path

from utils.utils import GroupTypeSubscription, get_tokens_and_finish_dates

# Ініціалізуємо локалізацію
_ = I18n(path=Path(__file__).parent.parent / 'locales', domain='auction').gettext

# --- Конфігурація ---
BATCH_SIZE = 500  # Розмір батчу
CHECK_INTERVAL_SECONDS = 300  # Інтервал перевірки (секунди)

# Ініціалізуємо бота
bot = Bot(token=BOT_TOKEN, validate_token=False)


async def send_end_subscription_message(owner_id: str, group_id: str, group_title: str,
                                        type_subscription: GroupTypeSubscription):
    """
    Відправляє власнику групи та в групу повідомлення про закінчення підписки.
    """
    message = {
        "auction": {
            "owner_message": _("Підписка на аукціон закінчилася"),
            "group_message": _(
                "Роботу аукціону було призупинено на невизначений час, всі дані збережено. Для поновлення роботи зверніться до адміністратора бота."),
        },
        "ads": {
            "owner_message": _("Підписка на оголошення закінчилася"),
            "group_message": _(
                "Роботу оголошень було призупинено на невизначений час, всі дані збережено. Для поновлення роботи зверніться до адміністратора бота."),
        },
    }[type_subscription]
    owner_message = message.get('owner_message')
    group_message = message.get('group_message')
    # to owner
    chat_subscription = await GroupSubscriptionPlanService.get_subscription(group_id)
    sub_dates, tokens = await get_tokens_and_finish_dates(group_id, chat_subscription=chat_subscription)
    owner_kb = await activate_ad_auction_kb(auction_token=tokens[GroupTypeSubscription.AUCTION],
                                            ads_token=tokens[GroupTypeSubscription.ADVERTISEMENT], group_id=group_id,
                                            free_trial=chat_subscription.free_trial)
    await bot.send_message(chat_id=owner_id, text=f"{owner_message} '{group_title}'",
                           reply_markup=owner_kb)
    # to groups
    await bot.send_message(group_id, group_message)


async def process_expired_flags(session: AsyncSession):
    """
    Проходить по групах, у яких закінчився час `auction_time` або `ads_time`,
    оновлює відповідні флажки та повертає список груп.
    """
    current_timestamp = datetime.utcnow().timestamp()

    query = (
        select(GroupSubscriptionPlan)
        .options(selectinload(GroupSubscriptionPlan.group))
        .where(
            (GroupSubscriptionPlan.auction_sub_time < current_timestamp)
            &
            GroupSubscriptionPlan.auction_paid.is_(True)
            |
            (GroupSubscriptionPlan.ads_sub_time < current_timestamp)
            &
            GroupSubscriptionPlan.ads_paid.is_(True))
        .limit(BATCH_SIZE)
    )
    # Отримуємо групи батчами
    result = await session.execute(query)
    subscriptions = result.scalars().all()
    groups = []

    # Якщо немає груп, виходимо
    if not subscriptions:
        return groups
    # Оновлюємо флажки для груп
    for subscription in subscriptions:
        group = subscription.group
        groups.append(group)
        if subscription.auction_sub_time < current_timestamp and subscription.auction_paid:
            subscription.auction_paid = False  # функція стає безкоштовною
            await send_end_subscription_message(group.owner_telegram_id, group.chat_id, group.chat_name,
                                                GroupTypeSubscription.AUCTION)
        if subscription.ads_sub_time < current_timestamp and subscription.ads_paid:
            subscription.ads_paid = False  # функція стає безкоштовною
            await send_end_subscription_message(group.owner_telegram_id, group.chat_id, group.chat_name,
                                                GroupTypeSubscription.ADVERTISEMENT)

    # Зберігаємо зміни
    await session.commit()

    return groups


async def main():
    """
    Основний цикл перевірки груп і оновлення флажків.
    """
    retry_delay = 10  # Затримка між повторними спробами у разі помилки (секунди)
    error_count = 0
    while True:
        try:
            async with async_sessionmaker(engine, class_=AsyncSession)() as session:
                expired_groups = await process_expired_flags(session)

                # Чекаємо перед наступною перевіркою
                if not expired_groups:
                    logging.info("No expired groups found. Sleeping...")
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                error_count = 0
        except Exception as e:
            if error_count == 10:
                await bot.send_message(DEV_ID, f"Проблема з підключенням до бази даних: {e}")
            logging.exception(f"Error during processing: {e}")
            logging.info(f"Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            error_count += 1


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
