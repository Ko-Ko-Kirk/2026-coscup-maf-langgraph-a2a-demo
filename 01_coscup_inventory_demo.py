#!/usr/bin/env python3
"""COSCUP 2026 guided demo: MAF A2A tool → LangGraph inventory workflow.

The default offline mode intentionally needs no cloud account or API key. It
starts a real localhost A2A JSON-RPC service, discovers its Agent Card, wraps
the remote LangGraph agent with Microsoft Agent Framework's ``A2AAgent``, and
invokes the resulting ``FunctionTool`` once.

The full Microsoft Foundry path remains available through ``scripts/demo.sh``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from contextlib import suppress

import httpx
from agent_framework import AgentResponseUpdate

from agent_duet.client.collaboration import remote_agent, resolve_card
from agent_duet.scenarios.inventory.contracts import InventoryRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the credential-free COSCUP inventory demo over a real local A2A boundary."
    )
    parser.add_argument("--product", default="火雞肉飯")
    parser.add_argument("--quantity", type=int, default=20)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8003)
    return parser.parse_args()


def stage(number: int, title: str) -> None:
    print(f"\n[{number}/5] {title}", flush=True)


async def wait_for_health(base_url: str, server_process: asyncio.subprocess.Process) -> None:
    async with httpx.AsyncClient(timeout=0.5) as client:
        for _ in range(50):
            if server_process.returncode is not None:
                stderr = ""
                if server_process.stderr is not None:
                    stderr = (await server_process.stderr.read()).decode(errors="replace").strip()
                detail = f": {stderr}" if stderr else ""
                raise RuntimeError(f"The local A2A server stopped before becoming healthy{detail}")
            try:
                response = await client.get(f"{base_url}healthz")
                response.raise_for_status()
                return
            except httpx.HTTPError:
                await asyncio.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for {base_url}healthz")


def extract_decision(report: str) -> dict[str, object]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", report, flags=re.DOTALL)
    if match is None:
        raise ValueError("The A2A artifact did not contain the expected JSON decision")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise ValueError("The inventory decision must be a JSON object")
    return payload


def print_order_policy(decision: dict[str, object]) -> None:
    status = decision.get("status")
    can_fulfill = decision.get("can_fulfill")
    if status == "sufficient" and can_fulfill is True:
        outcome = "CONTINUE WITH CONTROLS"
        action = "Validate the catalog item and reserve stock before promising fulfillment."
    elif status == "insufficient":
        outcome = "DO NOT PROMISE FULFILLMENT"
        action = "Offer a smaller quantity, an alternative product, or human review."
    else:
        outcome = "MANUAL REVIEW"
        action = "Obtain a verified live observation before authorizing fulfillment."

    print(f"  Order policy: {outcome}")
    print(f"  Required next action: {action}")


async def run_demo(args: argparse.Namespace) -> None:
    request = InventoryRequest(product=args.product, quantity=args.quantity)
    base_url = f"http://{args.host}:{args.port}/"
    server_process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "agent_duet.scenarios.inventory.offline_server",
        "--host",
        args.host,
        "--port",
        str(args.port),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stage(1, "Start a real LangGraph inventory service in a child process")
        await wait_for_health(base_url, server_process)
        print(f"  Health check: {base_url}healthz → 200 OK")

        stage(2, "Discover the remote agent through its A2A v1 Agent Card")
        card = await resolve_card(base_url, timeout_seconds=10)
        print(f"  Agent: {card.name}")
        print(f"  Skill: {card.skills[0].id}")
        print(f"  Protocol: {card.supported_interfaces[0].protocol_binding}")

        updates: list[str] = []

        async def capture_update(update: AgentResponseUpdate) -> None:
            text = update.text.strip()
            if text and (not updates or updates[-1] != text):
                updates.append(text)
                print(f"  A2A update: {text}", flush=True)

        stage(3, "Wrap the remote LangGraph agent as a MAF FunctionTool")
        remote = remote_agent(card, base_url, timeout_seconds=30.0)
        tool = remote.as_tool(
            name="check_inventory_via_a2a",
            description="Check inventory through the remote LangGraph A2A specialist.",
            arg_name="request_json",
            stream_callback=capture_update,
            propagate_session=False,
        )
        tool.max_invocations = 1
        print(f"  Tool: {tool.name} (max_invocations={tool.max_invocations})")

        stage(4, "Send one order request across HTTP/JSON-RPC")
        print(f"  Request: {request.model_dump_json()}")
        async with remote:
            report = await tool.invoke(
                arguments={"request_json": request.model_dump_json()},
                skip_parsing=True,
            )
        if not isinstance(report, str):
            raise TypeError("The remote A2A tool did not return text")
        decision = extract_decision(report)
        observation = decision.get("observation")
        print(f"  Remote status: {decision.get('status')}")
        if isinstance(observation, dict):
            print(f"  Observed inventory: {observation.get('inventory')}")
            print(f"  Evidence source: {observation.get('source')}")

        stage(5, "Apply the outer order policy to the returned A2A artifact")
        print_order_policy(decision)
        print("\nDEMO PASSED: MAF A2A tool → HTTP/JSON-RPC → LangGraph → A2A artifact", flush=True)
    finally:
        if server_process.returncode is None:
            server_process.terminate()
            try:
                await asyncio.wait_for(server_process.wait(), timeout=5)
            except TimeoutError:
                server_process.kill()
                await server_process.wait()
        if server_process.stderr is not None:
            with suppress(Exception):
                await server_process.stderr.read()


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run_demo(args))
    except (OSError, RuntimeError, TypeError, ValueError, httpx.HTTPError) as exc:
        raise SystemExit(f"demo failed: {exc}") from exc


if __name__ == "__main__":
    main()
