"""Cross-framework collaboration over A2A using MAF's remote-agent abstraction."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx
from a2a.client import A2ACardResolver
from a2a.types import AgentCard
from agent_framework import AgentSession
from agent_framework.a2a import A2AAgent

from agent_duet.prompts import build_peer_review_prompt, build_synthesis_prompt


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Independent responses to the same architecture brief."""

    maf: str
    langgraph: str


@dataclass(frozen=True, slots=True)
class CollaborationResult:
    """Three A2A turns in the mediated peer-review protocol."""

    maf_initial_review: str
    langgraph_peer_review: str
    maf_final_synthesis: str


async def resolve_card(base_url: str, *, timeout_seconds: float) -> AgentCard:
    """Discover and return a remote Agent Card from the standard well-known URI."""
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        resolver = A2ACardResolver(httpx_client=client, base_url=base_url)
        return await resolver.get_agent_card()


def remote_agent(card: AgentCard, base_url: str, *, timeout_seconds: float) -> A2AAgent:
    """Wrap any discovered endpoint as the same MAF Agent abstraction."""
    return A2AAgent(
        name=card.name,
        description=card.description,
        agent_card=card,
        url=base_url,
        timeout=timeout_seconds,
        supported_protocol_bindings=["JSONRPC"],
    )


async def compare_agents(
    *,
    task: str,
    maf_url: str,
    langgraph_url: str,
    timeout_seconds: float,
) -> ComparisonResult:
    """Send the same task to both agents over A2A for an apples-to-apples comparison."""
    maf_card, langgraph_card = await asyncio.gather(
        resolve_card(maf_url, timeout_seconds=timeout_seconds),
        resolve_card(langgraph_url, timeout_seconds=timeout_seconds),
    )
    maf = remote_agent(maf_card, maf_url, timeout_seconds=timeout_seconds)
    langgraph = remote_agent(langgraph_card, langgraph_url, timeout_seconds=timeout_seconds)

    async with maf, langgraph:
        maf_response, langgraph_response = await asyncio.gather(
            maf.run(task),
            langgraph.run(task),
        )

    return ComparisonResult(
        maf=maf_response.text,
        langgraph=langgraph_response.text,
    )


async def collaborate(
    *,
    task: str,
    maf_url: str,
    langgraph_url: str,
    timeout_seconds: float,
) -> CollaborationResult:
    """Run a MAF → LangGraph → MAF peer review entirely over A2A.

    A coordinator deliberately relays only user-visible artifacts. The agents
    do not share hidden state, tool implementations, or framework internals.
    """
    maf_card, langgraph_card = await asyncio.gather(
        resolve_card(maf_url, timeout_seconds=timeout_seconds),
        resolve_card(langgraph_url, timeout_seconds=timeout_seconds),
    )
    maf = remote_agent(maf_card, maf_url, timeout_seconds=timeout_seconds)
    langgraph = remote_agent(langgraph_card, langgraph_url, timeout_seconds=timeout_seconds)

    async with maf, langgraph:
        maf_session: AgentSession = maf.create_session()
        langgraph_session: AgentSession = langgraph.create_session()

        maf_initial = await maf.run(task, session=maf_session)
        peer_prompt = build_peer_review_prompt(
            original_brief=task,
            maf_review=maf_initial.text,
        )
        langgraph_review = await langgraph.run(peer_prompt, session=langgraph_session)
        synthesis_prompt = build_synthesis_prompt(
            original_brief=task,
            prior_review=maf_initial.text,
            peer_critique=langgraph_review.text,
        )
        maf_final = await maf.run(synthesis_prompt, session=maf_session)

    return CollaborationResult(
        maf_initial_review=maf_initial.text,
        langgraph_peer_review=langgraph_review.text,
        maf_final_synthesis=maf_final.text,
    )
