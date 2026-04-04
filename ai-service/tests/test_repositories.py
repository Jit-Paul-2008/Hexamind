from __future__ import annotations

import os
import tempfile
import sys
import unittest
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from database.connection import Base
from database.models import Case, Organization, Project


class RepositorySmokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "repo-test.db")
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", pool_pre_ping=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self.temp_dir.cleanup()

    async def test_create_project_case_records(self) -> None:
        async with self.session_factory() as session:
            org = Organization(name="Org", slug="org-smoke")
            session.add(org)
            await session.flush()

            project = Project(org_id=org.id, name="Project", description="desc")
            session.add(project)
            await session.flush()

            case = Case(project_id=project.id, name="Case", initial_question="What should we do?")
            session.add(case)
            await session.commit()

            rows = (await session.execute(select(Case))).scalars().all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].name, "Case")


if __name__ == "__main__":
    unittest.main()
