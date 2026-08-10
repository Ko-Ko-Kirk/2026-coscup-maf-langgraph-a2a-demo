#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

MODE="${1:-collaborate}"
if [[ "${MODE}" != "cards" && "${MODE}" != "compare" && "${MODE}" != "collaborate" && "${MODE}" != "inventory" ]]; then
  echo "usage: $0 [cards|compare|collaborate|inventory] [command options]" >&2
  exit 2
fi
shift || true

if [[ ! -f .env ]]; then
  echo "error: create .env from .env.example and configure Microsoft Foundry first" >&2
  exit 1
fi

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  if [[ -n "${MAF_PID:-}" ]]; then
    kill "${MAF_PID}" 2>/dev/null || true
  fi
  if [[ -n "${LANGGRAPH_PID:-}" ]]; then
    kill "${LANGGRAPH_PID}" 2>/dev/null || true
  fi
  if [[ -n "${INVENTORY_PID:-}" ]]; then
    kill "${INVENTORY_PID}" 2>/dev/null || true
  fi
  wait "${MAF_PID:-}" "${LANGGRAPH_PID:-}" "${INVENTORY_PID:-}" 2>/dev/null || true
  exit "${status}"
}
trap cleanup EXIT INT TERM

wait_for_health() {
  local name="$1"
  local url="$2"
  local pid="$3"

  for _ in {1..30}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      echo "error: ${name} exited before becoming ready; inspect .${name}-server.log" >&2
      return 1
    fi
    if curl --fail --silent --show-error --max-time 2 "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "error: ${name} did not become healthy; inspect .${name}-server.log" >&2
  return 1
}

if [[ "${MODE}" == "inventory" ]]; then
  uv run --locked langgraph-inventory-a2a-server >.inventory-server.log 2>&1 &
  INVENTORY_PID=$!
  wait_for_health "inventory" "http://127.0.0.1:8003/healthz" "${INVENTORY_PID}"
  uv run --locked agent-duet inventory "$@"
else
  uv run --locked maf-a2a-server >.maf-server.log 2>&1 &
  MAF_PID=$!
  uv run --locked langgraph-a2a-server >.langgraph-server.log 2>&1 &
  LANGGRAPH_PID=$!

  wait_for_health "maf" "http://127.0.0.1:8001/healthz" "${MAF_PID}"
  wait_for_health "langgraph" "http://127.0.0.1:8002/healthz" "${LANGGRAPH_PID}"

  uv run --locked agent-duet "${MODE}" "$@"
fi
