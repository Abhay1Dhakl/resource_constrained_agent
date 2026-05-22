import os

from resource_agent.config import load_env_file
from resource_agent.llm.mock_client import MockLLMClient
from resource_agent.llm.openai_client import OpenAILLMClient


def build_llm_client():
    load_env_file()
    provider = os.getenv("RESOURCE_AGENT_LLM_PROVIDER", "mock").strip().lower()

    if provider == "openai":
        return OpenAILLMClient()

    if provider == "mock":
        return MockLLMClient()

    raise ValueError(
        f"Unsupported RESOURCE_AGENT_LLM_PROVIDER='{provider}'. Use 'mock' or 'openai'."
    )
