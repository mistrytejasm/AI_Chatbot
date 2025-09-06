from typing import List, Dict, Any
from langchain_community.tools.tavily_search import TavilySearchResults
from core.dependencies import get_search_tool
from utils.formatters import ResponseFormatter


class SearchService:
    def __init__(self):
        self.search_tool = get_search_tool()
        self.formatter = ResponseFormatter()

    async def perform_search(self, query: str) -> Dict[str, Any]:
        """Perform web search and return formatted results"""
        try:
            if not self.search_tool:
                return {
                    "success": False,
                    "error": "Search tool not available",
                    "urls": [],
                    "query": query
                }

            search_results = await self.search_tool.ainvoke({"query": query})
            urls = self.formatter.extract_urls_from_search_results(search_results)

            return {
                "success": True,
                "results": search_results,
                "urls": urls,
                "query": query
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "urls": [],
                "query": query
            }
