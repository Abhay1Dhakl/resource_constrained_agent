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
class WebSearchTool(BaseTool):
    name = "web_search_tool"
    description = ("Searches the web for information based on a query. It accepts a search query as input and returns relevant search results."
                     "This tool uses the Tavily API for web search functionality.")
    
    def __init__(self, api_key: str | None = None):
        load_env_file()
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

        if TavilyClient is not None and self.api_key:
            self.client = TavilyClient(api_key=self.api_key)
        
        else:
            self.client = None
    
    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        query = arguments.get("query")
        max_results = arguments.get("max_results", 5)
        topic = arguments.get("topic")

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
        """
        Normalizes the raw search results from Tavily into a consistent format.

        Each result will have:
        - title: The title of the search result
        - url: The URL of the search result
        - snippet: A brief snippet or summary of the content
        - source: The source or domain of the result
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
