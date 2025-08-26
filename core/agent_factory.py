"""Agent factory for creating and managing agents in EUNA MVP."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from services.database_service import db_service
from services.groq_service import groq_service
from tools.tool_registry import tool_registry
from tools.tool_executor import tool_executor

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating and managing different types of agents."""
    
    def __init__(self):
        self.default_agent_templates = {
            "SummarizerAgent": {
                "role": "Text summarization and key point extraction specialist",
                "capabilities": ["text_analysis", "summarization", "key_extraction"],
                "system_prompt": """You are a SummarizerAgent specialized in analyzing and summarizing text content.
Your role is to:
1. Extract key information from long texts
2. Create concise, accurate summaries
3. Identify main themes and important details
4. Present information in a structured format

Always provide clear, well-organized summaries that capture the essence of the original content.""",
                "preferred_tools": ["text_summarizer", "json_parser"]
            },
            "SearchAgent": {
                "role": "Web search and information gathering specialist",
                "capabilities": ["web_search", "information_gathering", "fact_checking"],
                "system_prompt": """You are a SearchAgent specialized in finding and gathering information from the web.
Your role is to:
1. Conduct effective web searches using relevant keywords
2. Gather comprehensive information from multiple sources
3. Verify information accuracy when possible
4. Organize findings in a structured format

Always provide reliable, well-sourced information with proper attribution.""",
                "preferred_tools": ["web_search", "http_request", "json_parser"]
            },
            "CodingAgent": {
                "role": "Code generation, review, and debugging specialist",
                "capabilities": ["code_generation", "code_review", "debugging", "syntax_checking"],
                "system_prompt": """You are a CodingAgent specialized in software development tasks.
Your role is to:
1. Generate clean, efficient, and well-documented code
2. Review code for bugs, security issues, and best practices
3. Debug existing code and suggest improvements
4. Provide explanations for code functionality

Always follow coding best practices and provide clear explanations.""",
                "preferred_tools": ["file_reader", "json_parser", "http_request"]
            },
            "SchedulerAgent": {
                "role": "Task scheduling and time management specialist",
                "capabilities": ["scheduling", "time_management", "calendar_operations"],
                "system_prompt": """You are a SchedulerAgent specialized in organizing and managing schedules.
Your role is to:
1. Create and manage schedules and timelines
2. Optimize time allocation for tasks
3. Handle calendar operations and reminders
4. Provide time management recommendations

Always consider time zones, priorities, and dependencies when scheduling.""",
                "preferred_tools": ["datetime_tool", "calculator", "json_parser"]
            }
        }
    
    async def create_default_agent(self, task_id: int, agent_type: str, role: str) -> Dict[str, Any]:
        """Create a default agent of specified type."""
        
        template = self.default_agent_templates.get(agent_type)
        if not template:
            # Create generic agent if type not found
            template = {
                "role": role,
                "capabilities": ["general_reasoning"],
                "system_prompt": f"You are a {agent_type} agent. {role}",
                "preferred_tools": ["web_search", "calculator"]
            }
        
        # Create agent in database
        agent = await db_service.create_agent(
            task_id=task_id,
            name=agent_type,
            agent_type="default",
            role=template["role"],
            capabilities=template["capabilities"],
            prompt_template=template["system_prompt"]
        )
        
        logger.info(f"Created default agent {agent_type} for task {task_id}")
        
        return {
            "id": agent.id,
            "name": agent_type,
            "type": "default",
            "role": template["role"],
            "capabilities": template["capabilities"],
            "system_prompt": template["system_prompt"],
            "preferred_tools": template["preferred_tools"],
            "priority": "medium"
        }
    
    async def create_dynamic_agent(self, task_id: int, agent_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create a dynamic agent based on GROQ-generated definition."""
        
        name = agent_definition.get("name", "DynamicAgent")
        role = agent_definition.get("role", "Specialized task agent")
        capabilities = agent_definition.get("capabilities", [])
        system_prompt = agent_definition.get("system_prompt", "")
        
        # Create agent in database
        agent = await db_service.create_agent(
            task_id=task_id,
            name=name,
            agent_type="dynamic",
            role=role,
            capabilities=capabilities,
            prompt_template=system_prompt
        )
        
        logger.info(f"Created dynamic agent {name} for task {task_id}")
        
        return {
            "id": agent.id,
            "name": name,
            "type": "dynamic",
            "role": role,
            "capabilities": capabilities,
            "system_prompt": system_prompt,
            "preferred_tools": agent_definition.get("preferred_tools", []),
            "specialization": agent_definition.get("specialization", "General"),
            "priority": "high"  # Dynamic agents typically have higher priority
        }
    
    async def execute_agent(self, agent_id: int, task_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an agent with given input and context."""
        
        try:
            # Get agent details from database
            agents = await db_service.get_task_agents(task_id=None)  # We'll filter by agent_id
            agent = None
            for a in agents:
                if a.id == agent_id:
                    agent = a
                    break
            
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Update agent status
            await db_service.update_agent_status(agent_id, "active")
            
            # Get agent's preferred tools
            capabilities = agent.capabilities or []
            preferred_tools = tool_registry.get_tools_for_capabilities(capabilities)
            
            # Execute agent reasoning using GROQ
            reasoning_result = await groq_service.execute_agent_reasoning(
                agent_prompt=agent.prompt_template,
                task_input=task_input,
                context=context,
                tools_available=preferred_tools
            )
            
            # Execute planned actions using tools
            tool_results = []
            planned_actions = reasoning_result.get("planned_actions", [])
            tools_needed = reasoning_result.get("tools_needed", [])
            
            for tool_name in tools_needed:
                if tool_name in [tool.name for tool in tool_registry.tools.values()]:
                    # Determine tool parameters based on context and reasoning
                    tool_params = await self._determine_tool_parameters(
                        tool_name, task_input, context, reasoning_result
                    )
                    
                    # Execute tool
                    tool_result = await tool_executor.execute_single_tool(
                        agent_id, tool_name, tool_params
                    )
                    tool_results.append(tool_result)
            
            # Compile agent result
            agent_result = {
                "success": True,
                "agent_id": agent_id,
                "agent_name": agent.name,
                "agent_type": agent.agent_type,
                "reasoning": reasoning_result.get("reasoning", ""),
                "planned_actions": planned_actions,
                "tools_used": [r["tool_name"] for r in tool_results if r["success"]],
                "tool_results": tool_results,
                "confidence_level": reasoning_result.get("confidence_level", "medium"),
                "output": self._synthesize_agent_output(reasoning_result, tool_results),
                "next_steps": reasoning_result.get("next_steps", [])
            }
            
            # Update agent status
            await db_service.update_agent_status(agent_id, "completed")
            
            logger.info(f"Agent {agent.name} executed successfully")
            return agent_result
            
        except Exception as e:
            logger.error(f"Error executing agent {agent_id}: {e}")
            
            # Update agent status
            await db_service.update_agent_status(agent_id, "failed")
            
            return {
                "success": False,
                "agent_id": agent_id,
                "agent_name": agent.name if 'agent' in locals() else "unknown",
                "error": str(e),
                "reasoning": "Agent execution failed due to error",
                "tools_used": [],
                "tool_results": [],
                "confidence_level": "low"
            }
    
    async def _determine_tool_parameters(self, tool_name: str, task_input: str, 
                                       context: Dict[str, Any], reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Determine appropriate parameters for tool execution."""
        
        # Basic parameter determination based on tool type and context
        params = {}
        
        if tool_name == "web_search":
            # Extract search query from task input or reasoning
            search_query = task_input
            if "search" in reasoning.get("reasoning", "").lower():
                # Try to extract more specific search terms
                reasoning_text = reasoning.get("reasoning", "")
                if "search for" in reasoning_text.lower():
                    start = reasoning_text.lower().find("search for") + 10
                    end = reasoning_text.find(".", start)
                    if end > start:
                        search_query = reasoning_text[start:end].strip()
            
            params = {
                "query": search_query,
                "max_results": 5
            }
        
        elif tool_name == "calculator":
            # Look for mathematical expressions in task input
            import re
            math_patterns = re.findall(r'[\d+\-*/().%\s]+', task_input)
            if math_patterns:
                params = {"expression": math_patterns[0].strip()}
            else:
                params = {"expression": "1+1"}  # Default safe expression
        
        elif tool_name == "text_summarizer":
            params = {
                "text": task_input,
                "max_sentences": 3
            }
        
        elif tool_name == "datetime_tool":
            params = {"operation": "now"}
        
        elif tool_name == "json_parser":
            # Look for JSON-like content in task input
            if "{" in task_input and "}" in task_input:
                start = task_input.find("{")
                end = task_input.rfind("}") + 1
                json_content = task_input[start:end]
                params = {"json_data": json_content}
            else:
                params = {"json_data": "{}"}
        
        else:
            # Generic parameters
            params = {"input": task_input}
        
        return params
    
    def _synthesize_agent_output(self, reasoning: Dict[str, Any], tool_results: List[Dict[str, Any]]) -> str:
        """Synthesize agent output from reasoning and tool results."""
        
        output_parts = []
        
        # Add reasoning summary
        if reasoning.get("reasoning"):
            output_parts.append(f"Analysis: {reasoning['reasoning']}")
        
        # Add tool results summary
        successful_tools = [r for r in tool_results if r["success"]]
        if successful_tools:
            output_parts.append("Tool Results:")
            for tool_result in successful_tools:
                tool_name = tool_result["tool_name"]
                result_summary = self._summarize_tool_result(tool_result)
                output_parts.append(f"- {tool_name}: {result_summary}")
        
        # Add expected outcome
        if reasoning.get("expected_outcome"):
            output_parts.append(f"Expected Outcome: {reasoning['expected_outcome']}")
        
        # Add next steps if any
        next_steps = reasoning.get("next_steps", [])
        if next_steps:
            output_parts.append("Next Steps:")
            for step in next_steps:
                output_parts.append(f"- {step}")
        
        return "\n\n".join(output_parts) if output_parts else "Agent completed processing."
    
    def _summarize_tool_result(self, tool_result: Dict[str, Any]) -> str:
        """Create a brief summary of tool result."""
        
        if not tool_result["success"]:
            return f"Failed - {tool_result.get('error', 'Unknown error')}"
        
        result = tool_result.get("result", {})
        tool_name = tool_result["tool_name"]
        
        if tool_name == "web_search":
            total_results = result.get("total_results", 0)
            return f"Found {total_results} search results"
        
        elif tool_name == "calculator":
            calc_result = result.get("result")
            return f"Calculated: {calc_result}"
        
        elif tool_name == "text_summarizer":
            summary_length = result.get("summary_length", 0)
            compression = result.get("compression_ratio", 0)
            return f"Created summary ({summary_length} chars, {compression:.1%} compression)"
        
        elif tool_name == "datetime_tool":
            current_time = result.get("current_datetime", "")
            return f"Current time: {current_time[:19]}"  # Remove microseconds
        
        else:
            return "Completed successfully"
    
    async def get_agent_capabilities(self, agent_type: str) -> List[str]:
        """Get capabilities for a specific agent type."""
        
        template = self.default_agent_templates.get(agent_type)
        if template:
            return template["capabilities"]
        
        return ["general_reasoning"]
    
    async def list_available_agent_types(self) -> Dict[str, Dict[str, Any]]:
        """List all available default agent types."""
        
        return {
            agent_type: {
                "role": template["role"],
                "capabilities": template["capabilities"],
                "description": template["system_prompt"][:100] + "..."
            }
            for agent_type, template in self.default_agent_templates.items()
        }


# Global agent factory instance
agent_factory = AgentFactory()
