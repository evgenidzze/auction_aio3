import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
from utils.config import DB_PASS, DB_NAME, DB_HOST, DB_USER, PORT
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{PORT}/{DB_NAME}"


async def async_main() -> None:
    engine = create_async_engine(url=DATABASE_URL, echo=True)
    async with engine.connect() as conn:
        res = await conn.execute(text('show tables;'))
        if 'alembic_version' in res.scalars().all():
            await conn.execute(text('TRUNCATE TABLE alembic_version;'))
    await engine.dispose()
asyncio.run(async_main())
