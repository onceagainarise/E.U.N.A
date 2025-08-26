"""Base agent class for EUNA MVP."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents in EUNA."""
    
    def __init__(self, agent_id: int, name: str, role: str, capabilities: List[str]):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.status = "initialized"
        self.created_at = datetime.now()
        self.execution_history: List[Dict[str, Any]] = []
    
    @abstractmethod
    async def execute(self, task_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main functionality."""
        pass
    
    @abstractmethod
    async def plan_actions(self, task_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan the actions needed to complete the task."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "capabilities": self.capabilities,
            "created_at": self.created_at.isoformat(),
            "execution_count": len(self.execution_history)
        }
    
    def log_execution(self, task_input: str, result: Dict[str, Any]):
        """Log execution for history tracking."""
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "task_input": task_input[:100] + "..." if len(task_input) > 100 else task_input,
            "success": result.get("success", False),
            "tools_used": result.get("tools_used", []),
            "confidence": result.get("confidence_level", "medium")
        }
        self.execution_history.append(execution_record)
        
        # Keep only last 10 executions
        if len(self.execution_history) > 10:
            self.execution_history = self.execution_history[-10:]
    
    def can_handle_capability(self, capability: str) -> bool:
        """Check if agent can handle a specific capability."""
        return capability in self.capabilities
    
    def get_preferred_tools(self) -> List[str]:
        """Get list of preferred tools for this agent type."""
        # Default implementation - can be overridden by subclasses
        capability_tool_mapping = {
            "web_search": ["web_search"],
            "text_analysis": ["text_summarizer"],
            "calculation": ["calculator"],
            "data_processing": ["json_parser"],
            "file_operations": ["file_reader"],
            "scheduling": ["datetime_tool"],
            "communication": ["http_request"]
        }
        
        preferred_tools = []
        for capability in self.capabilities:
            if capability in capability_tool_mapping:
                preferred_tools.extend(capability_tool_mapping[capability])
        
        return list(set(preferred_tools))  # Remove duplicates


class AgentExecutionContext:
    """Context object for agent execution."""
    
    def __init__(self, task_id: int, user_input: str, session_context: Optional[Dict] = None):
        self.task_id = task_id
        self.user_input = user_input
        self.session_context = session_context or {}
        self.execution_start = datetime.now()
        self.intermediate_results: Dict[str, Any] = {}
        self.tool_results: List[Dict[str, Any]] = []
    
    def add_intermediate_result(self, key: str, value: Any):
        """Add intermediate result for use by other agents."""
        self.intermediate_results[key] = value
    
    def get_intermediate_result(self, key: str, default: Any = None) -> Any:
        """Get intermediate result from previous processing."""
        return self.intermediate_results.get(key, default)
    
    def add_tool_result(self, tool_name: str, result: Dict[str, Any]):
        """Add tool execution result."""
        self.tool_results.append({
            "tool_name": tool_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_execution_duration(self) -> float:
        """Get execution duration in seconds."""
        return (datetime.now() - self.execution_start).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "task_id": self.task_id,
            "user_input": self.user_input,
            "session_context": self.session_context,
            "execution_start": self.execution_start.isoformat(),
            "intermediate_results": self.intermediate_results,
            "tool_results": self.tool_results,
            "execution_duration": self.get_execution_duration()
        }
