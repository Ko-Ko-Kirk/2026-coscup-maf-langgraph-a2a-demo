from pathlib import Path

import pytest

from agent_duet.settings import Settings


def test_public_clone_defaults_to_fixture_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("INVENTORY_MODE", raising=False)
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.inventory_mode == "fixture"
