# Source-code comparison

The comparison is controlled: same model deployment, domain functions, tool
names, prompt headings, A2A skill, and user brief.

## 1. Agent construction

MAF puts the loop behind an Agent abstraction:

```python
return Agent(
    client=client,
    name="MAF Enterprise Reviewer",
    instructions=MAF_SYSTEM_PROMPT,
    tools=MAF_TOOLS,
)
```

Source: [`src/agent_duet/maf/agent.py`](../src/agent_duet/maf/agent.py)

LangGraph makes the loop explicit:

```python
builder = StateGraph(MessagesState)
builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode(LANGGRAPH_TOOLS))
builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent",
    tools_condition,
    {"tools": "tools", "__end__": END},
)
builder.add_edge("tools", "agent")
```

Source:
[`src/agent_duet/langgraph/agent.py`](../src/agent_duet/langgraph/agent.py)

This is the central design comparison:

```text
MAF:       configure an agent; the framework owns the model/tool loop
LangGraph: configure a graph; application code exposes nodes and transitions
```

## 2. Tool parity

Both adapters call the same pure domain functions:

```text
lookup_enterprise_control
calculate_operational_risk
```

Framework adapters:

- [`src/agent_duet/maf/tools.py`](../src/agent_duet/maf/tools.py)
- [`src/agent_duet/langgraph/tools.py`](../src/agent_duet/langgraph/tools.py)
- [`src/agent_duet/domain.py`](../src/agent_duet/domain.py)

The parity test prevents a future change from giving one agent extra tools:

```python
assert maf_names == langgraph_names
```

It also normalizes adapter-only Pydantic titles and compares each tool's
description, required arguments, types, bounds, and field descriptions:

```python
assert maf_contracts == langgraph_contracts
```

This matters because matching Python function names alone does not guarantee
that the model receives the same function-calling schema.

## 3. Microsoft Foundry model parity

MAF:

```python
FoundryChatClient(
    project_endpoint=settings.foundry_project_endpoint,
    model=settings.foundry_model,
    credential=resolved_credential,
)
```

LangGraph:

```python
AzureAIOpenAIApiChatModel(
    project_endpoint=settings.foundry_project_endpoint,
    model=settings.foundry_model,
    credential=resolved_credential,
)
```

Both receive the same endpoint, deployment name, and Entra credential strategy.

## 4. A2A hosting

Both services publish an A2A v1 Agent Card and JSON-RPC route through
[`src/agent_duet/a2a_common.py`](../src/agent_duet/a2a_common.py).

MAF uses the upstream `A2AExecutor.handle_events` conversion logic, while the
application adds an explicit session retention policy:

```text
A2A context_id → InMemorySessionRegistry → AgentSession
```

Source:
[`src/agent_duet/maf/executor.py`](../src/agent_duet/maf/executor.py)

LangGraph owns its protocol adapter:

```text
A2A context_id → configurable.thread_id → checkpointer
```

Source:
[`src/agent_duet/langgraph/executor.py`](../src/agent_duet/langgraph/executor.py)

## 5. What is intentionally not normalized

The comparison should preserve meaningful framework differences:

- MAF and LangGraph use their native message/state types.
- MAF session storage and LangGraph checkpointing are not treated as equivalent.
- LangGraph exposes graph transitions; MAF exposes an Agent contract.
- A2A exchanges public artifacts, not internal state.

Normalizing these differences away would make the code shorter but the
framework comparison less honest.

## 6. Inventory scenario: composition versus control

The optional inventory scenario makes the two design philosophies interact.

MAF converts a remote A2A agent into a normal function tool:

```python
inventory_tool = remote_inventory_agent.as_tool(
    name="check_inventory_via_a2a",
    arg_name="request_json",
    propagate_session=False,
)
inventory_tool.max_invocations = 1

orchestrator = Agent(
    client=foundry_client,
    instructions=INVENTORY_ORCHESTRATOR_PROMPT,
    tools=[inventory_tool],
)
```

LangGraph retains explicit control of the remote decision:

```python
builder.add_edge(START, "parse_request")
builder.add_conditional_edges(
    "parse_request",
    route_after_parse,
    {
        "lookup_inventory": "lookup_inventory",
        "manual_review": "manual_review",
    },
)
builder.add_conditional_edges(
    "lookup_inventory",
    route_after_lookup,
    {
        "sufficient": "sufficient",
        "insufficient": "insufficient",
        "manual_review": "manual_review",
    },
)
```

This is not an attempt to make one runtime absorb the other:

```text
MAF decides whether to delegate.
A2A carries the remote invocation.
LangGraph controls the inventory execution path.
MAF receives only the public A2A result.
```

Source:

- [`orchestrator.py`](../src/agent_duet/scenarios/inventory/orchestrator.py)
- [`graph.py`](../src/agent_duet/scenarios/inventory/graph.py)
