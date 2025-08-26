"""Tool registry system for EUNA MVP."""

import logging
from typing import Dict, List, Any, Callable, Optional
from abc import ABC, abstractmethod
import asyncio
import inspect

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Abstract base class for all tools."""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.parameters = parameters or {}
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        pass
    
    def validate_parameters(self, **kwargs) -> bool:
        """Validate parameters before execution."""
        required_params = self.parameters.get("required", [])
        for param in required_params:
            if param not in kwargs:
                raise ValueError(f"Missing required parameter: {param}")
        return True


class ToolRegistry:
    """Registry for managing and executing tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.tool_categories: Dict[str, List[str]] = {
            "search": [],
            "computation": [],
            "communication": [],
            "data_processing": [],
            "file_operations": [],
            "general": []
        }
    
    def register_tool(self, tool: Tool, category: str = "general"):
        """Register a tool in the registry."""
        self.tools[tool.name] = tool
        if category in self.tool_categories:
            self.tool_categories[category].append(tool.name)
        else:
            self.tool_categories["general"].append(tool.name)
        
        logger.info(f"Registered tool: {tool.name} in category: {category}")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a category."""
        tool_names = self.tool_categories.get(category, [])
        return [self.tools[name] for name in tool_names if name in self.tools]
    
    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all available tools with their descriptions."""
        return {
            name: {
                "description": tool.description,
                "parameters": tool.parameters
            }
            for name, tool in self.tools.items()
        }
    
    def get_tools_for_capabilities(self, capabilities: List[str]) -> List[str]:
        """Get recommended tools for given capabilities."""
        capability_tool_mapping = {
            "web_search": ["web_search", "duckduckgo_search"],
            "calculation": ["calculator", "math_evaluator"],
            "data_analysis": ["csv_processor", "json_parser"],
            "file_processing": ["file_reader", "file_writer"],
            "communication": ["email_sender"],
            "scheduling": ["calendar_tool"],
            "code_generation": ["code_executor", "syntax_checker"],
            "summarization": ["text_summarizer"],
            "translation": ["language_translator"]
        }
        
        recommended_tools = []
        for capability in capabilities:
            if capability in capability_tool_mapping:
                recommended_tools.extend(capability_tool_mapping[capability])
        
        # Return only tools that are actually registered
        return [tool for tool in recommended_tools if tool in self.tools]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool with given parameters."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        try:
            # Validate parameters
            tool.validate_parameters(**kwargs)
            
            # Execute tool
            logger.info(f"Executing tool: {tool_name}")
            result = await tool.execute(**kwargs)
            
            logger.info(f"Tool {tool_name} executed successfully")
            return {
                "success": True,
                "tool_name": tool_name,
                "result": result,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "tool_name": tool_name,
                "result": None,
                "error": str(e)
            }
    
    async def execute_tool_chain(self, tool_chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a chain of tools in sequence."""
        results = []
        context = {}
        
        for step in tool_chain:
            tool_name = step.get("tool")
            parameters = step.get("parameters", {})
            
            # Replace context variables in parameters
            for key, value in parameters.items():
                if isinstance(value, str) and value.startswith("$context."):
                    context_key = value[9:]  # Remove "$context."
                    if context_key in context:
                        parameters[key] = context[context_key]
            
            # Execute tool
            result = await self.execute_tool(tool_name, **parameters)
            results.append(result)
            
            # Update context with result
            if result["success"]:
                context[f"{tool_name}_result"] = result["result"]
            
            # Stop chain if tool failed and no error handling specified
            if not result["success"] and not step.get("continue_on_error", False):
                break
        
        return results


# Global tool registry instance
tool_registry = ToolRegistry()
