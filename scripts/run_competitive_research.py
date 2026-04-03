from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


def _service_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "ai-service"


def _load_competitive_research():
    service_dir = _service_dir()
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))
    from competitive_research import (  # type: ignore
        DEFAULT_COMPETITIVE_TOPICS,
        build_default_provider_specs,
        load_latest_competitive_batch_report,
        run_competitive_batch,
        save_competitive_batch_report,
        update_competitive_results_ledger,
    )

    return (
        DEFAULT_COMPETITIVE_TOPICS,
        build_default_provider_specs,
        load_latest_competitive_batch_report,
        run_competitive_batch,
        save_competitive_batch_report,
        update_competitive_results_ledger,
    )


async def _run_async(args: argparse.Namespace) -> dict[str, object]:
    (
        default_topics,
        build_default_provider_specs,
        _load_latest,
        run_competitive_batch,
        save_competitive_batch_report,
        update_competitive_results_ledger,
    ) = _load_competitive_research()

    topics = list(default_topics)
    if args.topics_file:
        topics = [line.strip() for line in Path(args.topics_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit > 0:
        topics = topics[: args.limit]

    provider_specs = build_default_provider_specs()
    if args.providers:
        allowed = {item.strip() for item in args.providers.split(",") if item.strip()}
        provider_specs = tuple(spec for spec in provider_specs if spec.label in allowed)
        if not provider_specs:
            raise SystemExit("No valid providers selected.")

    report = await run_competitive_batch(queries=topics, provider_specs=provider_specs)
    markdown_path, json_path = save_competitive_batch_report(report, args.output or None)
    ledger_path = update_competitive_results_ledger(report, args.ledger or None)

    payload = {
        "batchName": report.batch_name,
        "generatedAt": report.generated_at,
        "topicCount": report.topic_count,
        "providerStats": report.provider_stats(),
        "markdownPath": markdown_path,
        "jsonPath": json_path,
        "ledgerPath": ledger_path,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a 20-topic ARIA vs Gemini vs GPT competitive research batch.")
    parser.add_argument("--topics-file", default="", help="Optional newline-delimited file of research topics.")
    parser.add_argument("--limit", type=int, default=20, help="Limit the number of topics from the default list.")
    parser.add_argument("--output", default="", help="Path for the consolidated markdown report.")
    parser.add_argument("--ledger", default="", help="Path to the ledger markdown file to update.")
    parser.add_argument("--providers", default="", help="Comma-separated subset of providers: ARIA,Gemini,GPT.")
    args = parser.parse_args()

    payload = asyncio.run(_run_async(args))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
