from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config


class MigrationTests(unittest.TestCase):
    def test_alembic_upgrade_head(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "migration-test.db")
            os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

            config = Config("ai-service/alembic.ini")
            script_location = Path(__file__).resolve().parents[1] / "database" / "migrations"
            config.set_main_option("script_location", str(script_location))
            command.upgrade(config, "head")

            self.assertTrue(os.path.exists(db_path))


if __name__ == "__main__":
    unittest.main()
