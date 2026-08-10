"""Command-line interface for discovery, comparison, and collaboration."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx
from google.protobuf.json_format import MessageToDict

from agent_duet.client.collaboration import (
    CollaborationResult,
    ComparisonResult,
    collaborate,
    compare_agents,
    resolve_card,
)
from agent_duet.scenarios.inventory.orchestrator import (
    InventoryScenarioResult,
    run_inventory_scenario,
)
from agent_duet.settings import get_settings

DEFAULT_TASK = """\
Review this proposed enterprise customer-support architecture:

- A model-driven agent classifies complaints and may issue refunds up to USD 5,000.
- Tool calls write directly to the payment service.
- The service retries a failed request up to three times.
- Conversation state is currently stored in process memory.
- A separate LangGraph agent maintained by another team performs policy review.
- The two services may communicate over A2A.

Decide whether this design is ready for production and list the controls required before launch.
"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-duet",
        description="Compare and connect MAF and LangGraph agents over A2A.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in [
        ("compare", "Send the same brief to both agents in parallel."),
        ("collaborate", "Run a MAF → LangGraph → MAF peer-review exchange."),
    ]:
        command = subparsers.add_parser(name, help=help_text)
        task_group = command.add_mutually_exclusive_group()
        task_group.add_argument("--task", help="Architecture brief as a command-line string.")
        task_group.add_argument(
            "--task-file",
            type=Path,
            help="Read the architecture brief from a UTF-8 file.",
        )

    subparsers.add_parser("cards", help="Discover and print both A2A Agent Cards.")
    inventory = subparsers.add_parser(
        "inventory",
        help="Run MAF → LangGraph inventory specialist over A2A.",
    )
    inventory.add_argument("--product", default="火雞肉飯", help="Product to check.")
    inventory.add_argument(
        "--quantity",
        type=int,
        default=20,
        help="Requested quantity from 1 to 10,000.",
    )
    return parser


def _load_task(args: argparse.Namespace) -> str:
    if args.task_file:
        return args.task_file.read_text(encoding="utf-8").strip()
    if args.task:
        return str(args.task).strip()
    return DEFAULT_TASK.strip()


def _section(title: str, body: str) -> None:
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}\n{body.strip()}\n")


def _print_comparison(result: ComparisonResult) -> None:
    _section("MAF REVIEW", result.maf)
    _section("LANGGRAPH REVIEW", result.langgraph)


def _print_collaboration(result: CollaborationResult) -> None:
    _section("ROUND 1 — MAF INITIAL REVIEW", result.maf_initial_review)
    _section("ROUND 2 — LANGGRAPH ADVERSARIAL PEER REVIEW", result.langgraph_peer_review)
    _section("ROUND 3 — MAF FINAL SYNTHESIS", result.maf_final_synthesis)


def _print_inventory(result: InventoryScenarioResult) -> None:
    _section("ORDER REQUEST", result.request.model_dump_json(indent=2))
    remote_evidence = "\n\n".join(result.remote_updates) or "(No streaming updates captured.)"
    _section("LANGGRAPH INVENTORY AGENT — A2A UPDATES", remote_evidence)
    _section("MAF ORDER ORCHESTRATOR — FINAL DECISION", result.final_response)


async def _run(args: argparse.Namespace) -> None:
    settings = get_settings()
    maf_url = str(settings.maf_public_url)
    langgraph_url = str(settings.langgraph_public_url)
    timeout_seconds = float(settings.a2a_timeout_seconds)

    if args.command == "cards":
        maf_card, langgraph_card = await asyncio.gather(
            resolve_card(maf_url, timeout_seconds=timeout_seconds),
            resolve_card(langgraph_url, timeout_seconds=timeout_seconds),
        )
        _section(
            "MAF AGENT CARD",
            str(MessageToDict(maf_card, preserving_proto_field_name=True)),
        )
        _section(
            "LANGGRAPH AGENT CARD",
            str(MessageToDict(langgraph_card, preserving_proto_field_name=True)),
        )
        return

    if args.command == "inventory":
        result = await run_inventory_scenario(
            settings=settings,
            product=str(args.product),
            quantity=int(args.quantity),
        )
        _print_inventory(result)
        return

    task = _load_task(args)
    if not task:
        raise ValueError("The architecture brief cannot be empty")

    if args.command == "compare":
        result = await compare_agents(
            task=task,
            maf_url=maf_url,
            langgraph_url=langgraph_url,
            timeout_seconds=timeout_seconds,
        )
        _print_comparison(result)
        return

    result = await collaborate(
        task=task,
        maf_url=maf_url,
        langgraph_url=langgraph_url,
        timeout_seconds=timeout_seconds,
    )
    _print_collaboration(result)


def main() -> None:
    """CLI entry point."""
    args = _parser().parse_args()
    try:
        asyncio.run(_run(args))
    except (OSError, RuntimeError, ValueError, httpx.HTTPError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
