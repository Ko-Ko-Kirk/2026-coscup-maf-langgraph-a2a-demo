"""HTTP gateway for the external inventory demo API."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol

import httpx
from pydantic import ValidationError

from agent_duet.scenarios.inventory.contracts import (
    InventoryAPIResponse,
    InventoryObservation,
    InventorySource,
)

DEFAULT_FIXTURE_INVENTORY: dict[str, int] = {
    "火雞肉飯": 30,
    "珍珠奶茶": 12,
    "雞排": 0,
}


class InventoryUnavailableError(RuntimeError):
    """Raised when no trustworthy live or configured fixture result is available."""


class SupportsInventoryLookup(Protocol):
    """Small gateway port consumed by the LangGraph workflow."""

    async def get_inventory(self, product: str) -> InventoryObservation:
        """Return one observation for a product."""
        ...


class InventoryGateway:
    """Call the live API once per workflow, with bounded retries and explicit fallback."""

    def __init__(
        self,
        *,
        base_url: str,
        mode: str,
        timeout_seconds: float,
        max_attempts: int,
        retry_delay_seconds: float,
        fallback_to_fixture: bool,
        client: httpx.AsyncClient | None = None,
        fixtures: Mapping[str, int] | None = None,
    ) -> None:
        if mode not in {"live", "fixture"}:
            raise ValueError("mode must be 'live' or 'fixture'")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self._base_url = base_url
        self._mode = mode
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._fallback_to_fixture = fallback_to_fixture
        self._client = client
        self._fixtures = dict(fixtures or DEFAULT_FIXTURE_INVENTORY)

    async def get_inventory(self, product: str) -> InventoryObservation:
        """Return a live observation or a visibly labelled fixture result."""
        normalized = product.strip()
        if not normalized:
            raise ValueError("product cannot be blank")

        if self._mode == "fixture":
            return self._fixture_observation(normalized, InventorySource.FIXTURE)

        try:
            return await self._get_live_inventory(normalized)
        except (httpx.HTTPError, ValidationError, ValueError) as exc:
            if not self._fallback_to_fixture:
                raise InventoryUnavailableError("Live inventory lookup failed") from exc
            return self._fixture_observation(
                normalized,
                InventorySource.FIXTURE_FALLBACK,
                warning=(
                    "The live inventory endpoint was unavailable or returned an invalid response. "
                    "This fallback observation must not authorize fulfillment."
                ),
            )

    async def _get_live_inventory(self, product: str) -> InventoryObservation:
        if self._client is not None:
            payload = await self._request_with_retries(self._client, product)
        else:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                payload = await self._request_with_retries(client, product)

        if payload.prod.strip() != product:
            raise ValueError("Inventory API returned a different product")

        return InventoryObservation(
            observation_id=str(uuid.uuid4()),
            product=payload.prod.strip(),
            inventory=payload.inventory,
            observed_at=datetime.now(UTC),
            source=InventorySource.LIVE,
            catalog_verified=False,
            warning=(
                "The demo API reports a quantity but does not prove catalog membership "
                "or reserve inventory."
            ),
        )

    async def _request_with_retries(
        self,
        client: httpx.AsyncClient,
        product: str,
    ) -> InventoryAPIResponse:
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await client.get(
                    self._base_url,
                    params={"prod": product},
                    timeout=self._timeout_seconds,
                )
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt < self._max_attempts:
                    await asyncio.sleep(self._retry_delay_seconds)
                    continue
                raise

            retryable = response.status_code == 429 or response.status_code >= 500
            if retryable and attempt < self._max_attempts:
                await asyncio.sleep(self._retry_delay_seconds)
                continue

            response.raise_for_status()
            return InventoryAPIResponse.model_validate(response.json())

        raise InventoryUnavailableError("Inventory retry loop ended without a response")

    def _fixture_observation(
        self,
        product: str,
        source: InventorySource,
        *,
        warning: str | None = None,
    ) -> InventoryObservation:
        known_product = product in self._fixtures
        stock = self._fixtures.get(product, 0)
        resolved_warning = warning
        if resolved_warning is None and not known_product:
            resolved_warning = "Product is absent from the fixture catalog; fixture stock is zero."

        return InventoryObservation(
            observation_id=str(uuid.uuid4()),
            product=product,
            inventory=stock,
            observed_at=datetime.now(UTC),
            source=source,
            catalog_verified=known_product,
            warning=resolved_warning,
        )
