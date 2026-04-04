from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from model_provider import LocalPipelineModelProvider
from pipeline import PipelineService

DEFAULT_TOPICS = (
    "How should a hospital network harden API gateways for patient-data interoperability?",
    "What is the most reliable architecture for zero-downtime schema migrations in fintech APIs?",
    "How can a logistics company secure real-time webhook ingestion at global scale?",
    "What controls are needed to make an AI research platform audit-ready in regulated industries?",
    "How should a SaaS company design resilient multi-tenant rate limiting without customer impact?",
    "What is the best incident-response blueprint for API abuse and key leakage events?",
)


async def _run_one(query: str) -> tuple[str, dict[str, object], str]:
    provider = LocalPipelineModelProvider("llama3.1:8b")
    service = PipelineService(
        storage_path=SERVICE_DIR / ".data" / "pipeline-sessions-random-topic.json",
        model_provider=provider,
    )
    session_id = service.start(query, tenant_id="random-topic-report")

    async for _event in service.stream_events(session_id, tenant_id="random-topic-report"):
        pass

    final_answer = service.get_final_report(session_id, tenant_id="random-topic-report")
    quality = service.get_quality_report(session_id, tenant_id="random-topic-report")
    return final_answer, quality, session_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one full random-topic report with the local pipeline.")
    parser.add_argument("--topic", default="", help="Optional explicit topic. If omitted, one is chosen at random.")
    args = parser.parse_args()

    query = args.topic.strip() or random.choice(DEFAULT_TOPICS)
    final_answer, quality, session_id = asyncio.run(_run_one(query))

    out_dir = SERVICE_DIR / ".data" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_file = out_dir / f"random-topic-full-report-{ts}.md"

    body = (
        "# Real-Time Random Topic Report\n\n"
        f"- Topic: {query}\n"
        f"- Session ID: {session_id}\n"
        f"- Generated At: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- Overall Score: {quality.get('overallScore', 0.0)}\n"
        f"- Trust Score: {quality.get('trustScore', 0.0)}\n\n"
        "## Full Report\n\n"
        f"{final_answer}\n"
    )
    out_file.write_text(body, encoding="utf-8")

    print(str(out_file))
    print(query)
    print(session_id)
    print(quality.get("overallScore", 0.0), quality.get("trustScore", 0.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
