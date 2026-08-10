# Architecture and runtime boundaries

## Deployment view

```mermaid
flowchart TB
    U["CLI / application"]
    CO["MAF composition layer<br/>two A2AAgent wrappers"]

    subgraph MAF["Process A — Microsoft Agent Framework"]
        MCARD["Agent Card"]
        MRPC["A2A JSON-RPC routes"]
        MEXEC["StatefulMAFA2AExecutor"]
        MSESSION["AgentSession registry"]
        MAGENT["Agent<br/>instructions · tools · client"]
        MTOOLS["Enterprise control tools"]
    end

    subgraph LG["Process B — LangGraph"]
        LCARD["Agent Card"]
        LRPC["A2A JSON-RPC routes"]
        LEXEC["LangGraphA2AExecutor"]
        GRAPH["StateGraph"]
        MODEL["agent node"]
        TOOLS["ToolNode"]
        CHECK["InMemorySaver"]
    end

    F["Microsoft Foundry project<br/>same model deployment"]

    U --> CO
    CO -->|"discover + send/stream"| MCARD
    CO -->|"discover + send/stream"| LCARD
    MCARD --> MRPC --> MEXEC
    MEXEC <--> MSESSION
    MEXEC --> MAGENT
    MAGENT <--> MTOOLS
    MAGENT --> F

    LCARD --> LRPC --> LEXEC --> GRAPH
    GRAPH --> MODEL
    MODEL -->|"tool_calls"| TOOLS
    TOOLS --> MODEL
    MODEL -->|"no tool_calls"| GRAPH
    GRAPH <--> CHECK
    MODEL --> F
```

## Conversation identity mapping

| Layer | MAF service | LangGraph service |
|---|---|---|
| A2A conversation | `context_id` | `context_id` |
| Framework key | `AgentSession.session_id` | `configurable.thread_id` |
| Mapping | `a2a:{context_id}` | `thread_id = context_id` |
| Demo storage | in-process registry | `InMemorySaver` |
| Production replacement | tenant-bound durable session store | persistent checkpointer |

The identifiers correlate state; they are not authentication tokens. A
production service must bind them to an authenticated tenant/user and authorize
every read or mutation.

## Protocol boundary

A2A crosses the service boundary with:

- Agent Card metadata and skills;
- user/agent messages;
- task status;
- public artifacts;
- context and task identifiers.

A2A does not cross the boundary with:

- MAF `AgentSession.state`;
- LangGraph `MessagesState`;
- checkpointer records;
- private tools or credentials;
- model-hidden reasoning;
- graph nodes and edges.

This separation is why the project calls the design **cross-runtime
composition**, not a shared runtime.

## Collaboration sequence

```mermaid
sequenceDiagram
    participant CLI as Collaboration runner
    participant MAF as MAF A2A Agent
    participant LG as LangGraph A2A Agent
    participant F as Microsoft Foundry

    CLI->>MAF: message/send(architecture brief)
    MAF->>F: model + tools
    F-->>MAF: initial review
    MAF-->>CLI: completed task + artifact

    CLI->>LG: message/send(brief + untrusted MAF artifact)
    Note over LG: contextId becomes thread_id
    LG->>F: explicit graph loop + tools
    F-->>LG: adversarial review
    LG-->>CLI: completed task + artifact

    CLI->>MAF: message/send(peer critique, same MAF context)
    MAF->>F: synthesis in retained AgentSession
    F-->>MAF: final recommendation
    MAF-->>CLI: completed task + artifact
```

The coordinator is intentional. Open protocols do not imply that agents should
autonomously discover and call arbitrary peers.

## Inventory composition sequence

The optional inventory scenario uses a different composition style from the
mediated peer review:

```mermaid
sequenceDiagram
    participant U as User
    participant M as Local MAF Order Orchestrator
    participant A as Remote A2AAgent function tool
    participant L as LangGraph Inventory Service
    participant API as Inventory Demo API
    participant F as Microsoft Foundry

    U->>M: product + quantity
    M->>F: model-driven tool selection
    F-->>M: check_inventory_via_a2a(JSON)
    M->>A: FunctionTool invocation
    A->>L: A2A JSON-RPC message/send
    Note over L: context_id becomes thread_id
    L->>API: one inventory GET
    API-->>L: observed quantity
    L->>L: explicit conditional edge
    L->>F: render fixed decision evidence
    F-->>L: explanation
    L-->>A: completed A2A artifact
    A-->>M: remote agent tool result
    M->>F: enterprise synthesis
    F-->>M: final order recommendation
```

This combines two MAF concepts without conflating them:

1. `A2AAgent` supplies the transport-level remote Agent abstraction.
2. `A2AAgent.as_tool()` supplies the model-driven composition abstraction.

MAF never executes the remote LangGraph graph. The outer agent receives only
the remote tool's public result, while LangGraph retains its own graph state,
checkpoint, inventory gateway, and Foundry model call.
