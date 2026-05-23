from resource_agent.config import load_env_file
from resource_agent.llm.openai_client import OpenAILLMClient


def build_llm_client():
    load_env_file()
    return OpenAILLMClient()
