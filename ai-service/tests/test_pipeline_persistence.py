from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from pipeline import PipelineService


class PipelinePersistenceTests(unittest.TestCase):
    def test_sessions_are_saved_and_reloaded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "pipeline-sessions.json"
            service = PipelineService(storage_path=storage_path)

            session_id = service.start("How should we ship the MVP?")

            self.assertTrue(storage_path.exists())
            self.assertTrue(service.has_session(session_id))

            reloaded_service = PipelineService(storage_path=storage_path)
            self.assertTrue(reloaded_service.has_session(session_id))
            self.assertEqual(reloaded_service._sessions[session_id].query, "How should we ship the MVP?")


if __name__ == "__main__":
    unittest.main()
