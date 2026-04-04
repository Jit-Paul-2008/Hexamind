from __future__ import annotations

import asyncio

from database.connection import async_session_factory, init_db
from database.models import Organization


async def seed() -> None:
    await init_db()
    async with async_session_factory() as session:
        session.add(Organization(name="Default Organization", slug="default-org"))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
