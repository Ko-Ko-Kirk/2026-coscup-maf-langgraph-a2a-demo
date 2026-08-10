from __future__ import annotations

from google.protobuf.json_format import MessageToDict

from agent_duet.a2a_common import LANGGRAPH_IDENTITY, MAF_IDENTITY, create_agent_card


def test_agent_cards_have_the_same_a2a_contract() -> None:
    maf = create_agent_card(MAF_IDENTITY, "http://localhost:8001")
    langgraph = create_agent_card(LANGGRAPH_IDENTITY, "http://localhost:8002")

    assert maf.capabilities.streaming is True
    assert langgraph.capabilities.streaming is True
    assert maf.skills[0].id == langgraph.skills[0].id == "review_agent_architecture"
    assert maf.supported_interfaces[0].protocol_binding == "JSONRPC"
    assert langgraph.supported_interfaces[0].protocol_version == "1.0"


def test_agent_card_serializes_as_a2a_v1_json() -> None:
    card = create_agent_card(MAF_IDENTITY, "http://localhost:8001")
    payload = MessageToDict(card, preserving_proto_field_name=True)

    assert payload["supported_interfaces"][0]["protocol_binding"] == "JSONRPC"
    assert payload["capabilities"]["streaming"] is True
    assert payload["skills"][0]["input_modes"] == ["text/plain"]
