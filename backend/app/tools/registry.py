from typing import Dict, Type, List
from .base import BaseTool
from .flights import FlightsTool
from .lodging import LodgingTool
from .events import EventsTool
from .weather import WeatherTool
from .transit import TransitTool
from .rag import RAGTool


class ToolRegistry:
    """Registry for managing all available tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register all default tools."""
        tools = [
            FlightsTool(),
            LodgingTool(),
            EventsTool(),
            WeatherTool(),
            TransitTool(),
            RAGTool()
        ]
        
        for tool in tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: BaseTool):
        """Register a tool in the registry."""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> BaseTool:
        """Get a tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry")
        return self._tools[name]
    
    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self._tools.keys())
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def get_tool_schemas(self) -> Dict[str, dict]:
        """Get JSON schemas for all tools."""
        schemas = {}
        for name, tool in self._tools.items():
            schemas[name] = tool.get_json_schema()
        return schemas


# Global tool registry instance
tool_registry = ToolRegistry()

