from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from core.config import settings

# Initialize shared dependencies
memory = MemorySaver()

def get_llm():
    """Get configured LLM instance"""
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is required. Please set it in your .env file.")

    return ChatGroq(
        model=settings.MODEL_NAME,
        temperature=settings.MODEL_TEMPERATURE,
        api_key=settings.GROQ_API_KEY
    )


def get_search_tool():
    """Get configured search tool with correct name"""
    if not settings.TAVILY_API_KEY:
        print("Warning: TAVILY_API_KEY not found. Search functionality will be limited.")
        return None

    # Initialize with correct parameters
    return TavilySearch(
        max_results=settings.MAX_SEARCH_RESULTS,
        api_key=settings.TAVILY_API_KEY
    )
