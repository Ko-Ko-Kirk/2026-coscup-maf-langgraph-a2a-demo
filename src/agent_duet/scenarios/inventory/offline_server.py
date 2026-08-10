"""Credential-free A2A server used by the guided COSCUP demo."""

from __future__ import annotations

import argparse

import uvicorn
from pydantic import HttpUrl

from agent_duet.scenarios.inventory.gateway import InventoryGateway
from agent_duet.scenarios.inventory.graph import build_inventory_graph
from agent_duet.scenarios.inventory.server import create_app
from agent_duet.settings import Settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the fixture-backed inventory A2A service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8003)
    return parser


def main() -> None:
    args = _parser().parse_args()
    base_url = f"http://{args.host}:{args.port}/"
    gateway = InventoryGateway(
        base_url="https://unused.example/inventory/",
        mode="fixture",
        timeout_seconds=1,
        max_attempts=1,
        retry_delay_seconds=0,
        fallback_to_fixture=False,
    )
    graph = build_inventory_graph(gateway)
    settings = Settings(
        inventory_agent_host=args.host,
        inventory_agent_port=args.port,
        inventory_agent_public_url=HttpUrl(base_url),
    )
    app = create_app(settings=settings, graph=graph)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
