"""Microsoft Entra credential selection for local and deployed workloads."""

from __future__ import annotations

from azure.core.credentials import TokenCredential
from azure.identity import AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential

from agent_duet.settings import Settings


def build_credential(settings: Settings) -> TokenCredential:
    """Build the same credential strategy for MAF and LangGraph.

    `cli` is predictable for a conference laptop. `default` is convenient for
    mixed developer/cloud environments. `managed_identity` is the recommended
    explicit production choice when the workload runs on Azure.
    """
    if settings.azure_credential_mode == "cli":
        return AzureCliCredential()
    if settings.azure_credential_mode == "managed_identity":
        return ManagedIdentityCredential(client_id=settings.azure_client_id)
    return DefaultAzureCredential()
