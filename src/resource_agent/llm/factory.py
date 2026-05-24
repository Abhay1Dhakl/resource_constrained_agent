from resource_agent.config import load_env_file
from resource_agent.llm.openai_client import OpenAILLMClient


def build_llm_client():
    """Build the default LLM client after loading environment variables.

    Returns:
        OpenAILLMClient: Configured planner client instance.
    """
    load_env_file()
    return OpenAILLMClient()
