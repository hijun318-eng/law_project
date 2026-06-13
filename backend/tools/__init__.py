from backend.tools.registry import registry
from backend.tools.news_search_tool import NewsSearchTool

def init_tools():
    registry.register(NewsSearchTool())