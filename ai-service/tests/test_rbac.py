from __future__ import annotations

import os
import sys
import asyncio
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

os.environ.setdefault("HEXAMIND_ENABLE_DATABASE_PERSISTENCE", "1")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./ai-service/.data/rbac-test.db")

from fastapi.testclient import TestClient
from database.connection import init_db
from main import app


class RbacSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        asyncio.run(init_db())
        self.client = TestClient(app)

    def test_me_requires_authentication(self) -> None:
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
