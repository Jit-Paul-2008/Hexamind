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
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./ai-service/.data/auth-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient
from database.connection import init_db
from main import app


class AuthApiTests(unittest.TestCase):
    def setUp(self) -> None:
        asyncio.run(init_db())
        self.client = TestClient(app)

    def test_register_login_and_me(self) -> None:
        register = self.client.post(
            "/api/auth/register",
            json={
                "email": "auth-test@example.com",
                "password": "supersecure123",
                "displayName": "Auth Tester",
            },
        )
        self.assertIn(register.status_code, {200, 409})

        login = self.client.post(
            "/api/auth/login",
            json={
                "email": "auth-test@example.com",
                "password": "supersecure123",
            },
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["accessToken"]

        me = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "auth-test@example.com")


if __name__ == "__main__":
    unittest.main()
