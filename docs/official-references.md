# Official references and verified baseline

The project was implemented against documentation and source available on
2026-07-26.

## Microsoft Agent Framework

- [Microsoft Agent Framework overview](https://learn.microsoft.com/en-us/agent-framework/overview/)
- [A2A Agent provider](https://learn.microsoft.com/en-us/agent-framework/agents/providers/agent-to-agent)
- [Agent-to-Agent journey](https://learn.microsoft.com/en-us/agent-framework/journey/agent-to-agent)
- [Agents as Tools](https://learn.microsoft.com/en-us/agent-framework/journey/agents-as-tools)
- [Foundry Responses API quickstart](https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/responses-api)
- [MAF repository](https://github.com/microsoft/agent-framework)

Source baseline used for the code reading:

```text
microsoft/agent-framework
commit 711d6f24aeaf1b842a21bad059ef70112e701901
```

Relevant implementation:

- [`A2AAgent`](https://github.com/microsoft/agent-framework/blob/711d6f24aeaf1b842a21bad059ef70112e701901/python/packages/a2a/agent_framework_a2a/_agent.py)
- [`A2AExecutor`](https://github.com/microsoft/agent-framework/blob/711d6f24aeaf1b842a21bad059ef70112e701901/python/packages/a2a/agent_framework_a2a/_a2a_executor.py)
- [`FoundryChatClient`](https://github.com/microsoft/agent-framework/blob/711d6f24aeaf1b842a21bad059ef70112e701901/python/packages/foundry/agent_framework_foundry/_chat_client.py)
- [MAF A2A hosting sample](https://github.com/microsoft/agent-framework/blob/711d6f24aeaf1b842a21bad059ef70112e701901/python/samples/04-hosting/a2a/a2a_server.py)

## LangGraph and Microsoft Foundry

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Agent Server A2A endpoint](https://docs.langchain.com/langsmith/server-a2a)
- [Use LangChain and LangGraph with Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/langchain)
- [`StateGraph` reference](https://reference.langchain.com/python/langgraph/graph/state/StateGraph)
- [`ToolNode` reference](https://reference.langchain.com/python/langgraph.prebuilt/tool_node/ToolNode)

Source baseline used for the code reading:

```text
langchain-ai/langgraph
commit a7a27dd43a4229c2ca09ac065a6a39e4ce083063
```

Relevant implementation:

- [`StateGraph`](https://github.com/langchain-ai/langgraph/blob/a7a27dd43a4229c2ca09ac065a6a39e4ce083063/libs/langgraph/langgraph/graph/state.py)
- [Pregel loop](https://github.com/langchain-ai/langgraph/blob/a7a27dd43a4229c2ca09ac065a6a39e4ce083063/libs/langgraph/langgraph/pregel/_loop.py)
- [`ToolNode`](https://github.com/langchain-ai/langgraph/blob/a7a27dd43a4229c2ca09ac065a6a39e4ce083063/libs/prebuilt/langgraph/prebuilt/tool_node.py)

## A2A

- [A2A specification and repository](https://github.com/a2aproject/A2A)
- [A2A Python SDK](https://github.com/a2aproject/a2a-python)
- [Official LangGraph A2A sample](https://github.com/a2aproject/a2a-samples/tree/main/samples/python/agents/langgraph)

The application targets A2A v1 and disables the optional v0.3 compatibility
route. The lockfile resolves `a2a-sdk==1.1.2`.

## Resolved package versions

```text
agent-framework-core       1.12.1
agent-framework-foundry    1.10.3
agent-framework-a2a        1.0.0b260721
langgraph                  1.2.9
langchain-azure-ai         1.2.3
a2a-sdk                    1.1.2
```

These versions are recorded in `uv.lock`. Do not upgrade the protocol or agent
framework packages independently without rerunning the A2A round-trip tests.

## Demo dependency

- [Ko Ko inventory demo API](https://koko-demo-api.azurewebsites.net/inventory/?prod=%E7%81%AB%E9%9B%9E%E8%82%89%E9%A3%AF)

The inventory endpoint is treated as an untrusted, non-durable demonstration
dependency rather than an authoritative catalog or reservation system.
