"""The Microsoft Agent Framework implementation under comparison."""

from __future__ import annotations

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.core.credentials import TokenCredential

from agent_duet.auth import build_credential
from agent_duet.maf.tools import MAF_TOOLS
from agent_duet.prompts import MAF_SYSTEM_PROMPT
from agent_duet.settings import Settings


def build_maf_agent(client: FoundryChatClient) -> Agent:
    """Build the MAF reviewer.

    MAF owns the model-driven agent loop. Instructions, tools, and the model
    client are declared on `Agent`; the framework decides when to call tools
    and when the run is complete.
    """
    return Agent(
        client=client,
        name="MAF Enterprise Reviewer",
        description="Enterprise architecture reviewer implemented with Microsoft Agent Framework.",
        instructions=MAF_SYSTEM_PROMPT,
        tools=MAF_TOOLS,
    )


def build_live_maf_agent(settings: Settings, credential: TokenCredential | None = None) -> Agent:
    """Create the live MAF reviewer backed by Microsoft Foundry."""
    settings.require_foundry()
    resolved_credential = credential or build_credential(settings)
    client = FoundryChatClient(
        project_endpoint=settings.foundry_project_endpoint,
        model=settings.foundry_model,
        credential=resolved_credential,
    )
    return build_maf_agent(client)
