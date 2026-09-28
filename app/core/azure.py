from functools import lru_cache

from azure.identity import DefaultAzureCredential


@lru_cache
def get_azure_credential() -> DefaultAzureCredential:
    """Use the developer's Azure CLI identity locally and managed identity in Azure."""
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)
