import os
from typing import Dict, Any, List
from resource_agent.tools.base import BaseTool, ToolResult
from resource_agent.config import load_env_file
from concurrent.futures import ThreadPoolExecutor, TimeoutError

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

TIMEOUT_SECONDS = 10
DEFAULT_MAX_RESULTS = 5
MAX_MAX_RESULTS = 10
ALLOWED_TOPICS = {"general", "news"}

class WebSearchTool(BaseTool):
    name = "web_search_tool"
    description = ("Searches the web for information based on a query. It accepts a search query as input and returns relevant search results."
                     "This tool uses the Tavily API for web search functionality.")
    
    def __init__(self, api_key: str | None = None):
        """Configure the Tavily-backed web search tool.

        Args:
            api_key: Optional Tavily API key override.
        """
        load_env_file()
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

        if TavilyClient is not None and self.api_key:
            self.client = TavilyClient(api_key=self.api_key)
        
        else:
            self.client = None
    
    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a web search request with input validation and timeout.

        Args:
            arguments: Tool payload containing `query`, `max_results`, and an
                optional `topic`.

        Returns:
            ToolResult: Search response with answer and normalized sources, or
                an error payload.
        """
        query = arguments.get("query")
        max_results = arguments.get("max_results", DEFAULT_MAX_RESULTS)
        topic = arguments.get("topic")
        
        if not isinstance(max_results, int):
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message="max_results must be an integer.",
            )

        if max_results < 1 or max_results > MAX_MAX_RESULTS:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"max_results must be between 1 and {MAX_MAX_RESULTS}.",
            )
        
        if topic is not None and topic not in ALLOWED_TOPICS:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"topic must be one of: {sorted(ALLOWED_TOPICS)}.",
            )
        if not query:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message="No search query provided."
            )
        
        if TavilyClient is None:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message="Tavily library is not installed. Please install it to use the web search tool."
            )
        
        if not self.api_key:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message="Tavily API key is not set. Please provide an API key to use the web search tool."
            )
        
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.client.search, query=query, topic=topic, max_results=max_results, include_answer=True)
                search_response = future.result(timeout=TIMEOUT_SECONDS)
            sources = self._normalize_results(search_response.get("results", []), max_results)

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "query": query,
                    "topic": topic,
                    "answer": search_response.get("answer", ""),
                    "sources": sources,
                }
            )
        
        except TimeoutError:
            return ToolResult(
                success= False,
                tool_name=self.name,
                error_message=f"Web search timed out after {TIMEOUT_SECONDS} seconds."
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(exc)
            )
    
    def _normalize_results(self, results: List[Dict[str, Any]], max_results: int) -> List[Dict[str, Any]]:
        """Normalize raw Tavily results into the agent's source schema.

        Args:
            results: Raw Tavily search result list.
            max_results: Maximum number of sources to keep.

        Returns:
            List[Dict[str, Any]]: Normalized source entries for the agent.
        """

        normalized = []
        for result in results[:max_results]:
            content = result.get("content") or result.get("snippet", "")
            normalized.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": content,
                "snippet": content,
                "source": result.get("source", ""),
            })
        
        return normalized
