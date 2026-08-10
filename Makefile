.PHONY: install check test demo-offline compare collaborate inventory cards docker-up docker-down

install:
	uv sync --locked --all-groups

check:
	./scripts/check.sh

test:
	uv run --locked pytest

demo-offline:
	uv run --locked python 01_coscup_inventory_demo.py

compare:
	uv run --locked agent-duet compare

collaborate:
	uv run --locked agent-duet collaborate

inventory:
	uv run --locked agent-duet inventory --product 火雞肉飯 --quantity 20

cards:
	uv run --locked agent-duet cards

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
