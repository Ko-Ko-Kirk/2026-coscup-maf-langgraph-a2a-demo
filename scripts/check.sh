#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

uv sync --locked --all-groups
uv run --locked ruff check 01_coscup_inventory_demo.py scripts src tests
uv run --locked pyright 01_coscup_inventory_demo.py src tests
uv run --locked pytest
