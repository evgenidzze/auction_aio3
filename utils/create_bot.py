import asyncio
import time
from pathlib import Path
import aioredis
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.i18n import I18n, I18nMiddleware
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler_di import ContextSchedulerDecorator
from redis.asyncio import Redis


from aiogram.fsm.storage.redis import RedisStorage as RedisStorageDisp
from utils.config import BOT_TOKEN, REDIS_HOST, REDIS_PASS


def async_to_sync(awaitable):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(awaitable)


job_stores = {
    "default": RedisJobStore(jobs_key="dispatched_trips_jobs", run_times_key="dispatched_trips_running",
                             host=REDIS_HOST, port=6379, password=REDIS_PASS
                             )}
scheduler = AsyncIOScheduler(jobstores=job_stores)
# connection = async_to_sync(aioredis.from_url(f'redis://{REDIS_PASS}@{REDIS_HOST}'))
I18N_DOMAIN = 'auction'
BASE_DIR = Path(__file__).parent.parent
LOCALES_DIR = BASE_DIR / 'locales'
i18n = I18n(path=LOCALES_DIR, domain=I18N_DOMAIN)
_ = i18n.gettext
redis = Redis(host=REDIS_HOST, password=REDIS_PASS)
storage = RedisStorageDisp(redis=redis)

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode='html'))
dp = Dispatcher(storage=storage)

for job in scheduler.get_jobs():
    print(f"Job ID: {job.id}, Next Run Time: {job.next_run_time}")