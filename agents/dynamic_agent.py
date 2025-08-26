"""Dynamic agent implementation for EUNA MVP."""

import logging
from typing import Dict, List, Any, Optional

from agents.base_agent import BaseAgent, AgentExecutionContext
from services.groq_service import groq_service
from tools.tool_executor import tool_executor

logger = logging.getLogger(__name__)


class DynamicAgent(BaseAgent):
    """Dynamically generated agent based on GROQ-created specifications."""
    
    def __init__(self, agent_id: int, agent_definition: Dict[str, Any]):
        super().__init__(
            agent_id=agent_id,
            name=agent_definition.get("name", "DynamicAgent"),
            role=agent_definition.get("role", "Specialized task agent"),
            capabilities=agent_definition.get("capabilities", ["general_reasoning"])
        )
        
        self.system_prompt = agent_definition.get("system_prompt", "")
        self.specialization = agent_definition.get("specialization", "General")
        self.preferred_tools = agent_definition.get("preferred_tools", [])
        self.success_criteria = agent_definition.get("success_criteria", [])
        self.validation_steps = agent_definition.get("validation_steps", [])
        self.agent_definition = agent_definition
    
    async def execute(self, task_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute dynamic agent task using GROQ reasoning."""
        
        self.status = "active"
        execution_context = AgentExecutionContext(
            task_id=context.get("task_id", 0),
            user_input=task_input,
            session_context=context
        )
        
        try:
            # Use GROQ for agent reasoning
            reasoning_result = await groq_service.execute_agent_reasoning(
                agent_prompt=self.system_prompt,
                task_input=task_input,
                context=context,
                tools_available=self.preferred_tools
            )
            
            # Execute planned tools
            tool_results = []
            tools_needed = reasoning_result.get("tools_needed", [])
            
            for tool_name in tools_needed:
                if tool_name in self.preferred_tools:
                    # Determine tool parameters based on reasoning
                    tool_params = await self._determine_tool_parameters(
                        tool_name, task_input, context, reasoning_result
                    )
                    
                    # Execute tool
                    tool_result = await tool_executor.execute_single_tool(
                        agent_id=self.agent_id,
                        tool_name=tool_name,
                        parameters=tool_params
                    )
                    
                    tool_results.append(tool_result)
                    execution_context.add_tool_result(tool_name, tool_result)
            
            # Validate results against success criteria
            validation_result = await self._validate_results(
                reasoning_result, tool_results, task_input
            )
            
            # Compile final result
            result = {
                "success": validation_result["success"],
                "agent_name": self.name,
                "agent_type": "dynamic",
                "specialization": self.specialization,
                "reasoning": reasoning_result.get("reasoning", ""),
                "planned_actions": reasoning_result.get("planned_actions", []),
                "tools_used": [r["tool_name"] for r in tool_results if r["success"]],
                "tool_results": tool_results,
                "validation": validation_result,
                "confidence_level": reasoning_result.get("confidence_level", "medium"),
                "output": self._synthesize_output(reasoning_result, tool_results, validation_result),
                "next_steps": reasoning_result.get("next_steps", []),
                "execution_time": execution_context.get_execution_duration()
            }
            
            self.status = "completed"
            self.log_execution(task_input, result)
            
            return result
            
        except Exception as e:
            logger.error(f"DynamicAgent {self.name} execution error: {e}")
            self.status = "failed"
            
            result = {
                "success": False,
                "agent_name": self.name,
                "agent_type": "dynamic",
                "error": str(e),
                "tools_used": [],
                "confidence_level": "low"
            }
            
            self.log_execution(task_input, result)
            return result
    
    async def plan_actions(self, task_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan actions using GROQ reasoning."""
        
        try:
            reasoning_result = await groq_service.execute_agent_reasoning(
                agent_prompt=self.system_prompt,
                task_input=task_input,
                context=context,
                tools_available=self.preferred_tools
            )
            
            planned_actions = reasoning_result.get("planned_actions", [])
            tools_needed = reasoning_result.get("tools_needed", [])
            
            # Convert to action format
            actions = []
            for i, action in enumerate(planned_actions):
                tool_name = tools_needed[i] if i < len(tools_needed) else "internal_processing"
                actions.append({
                    "action": action,
                    "tool": tool_name,
                    "priority": "high" if i < 2 else "medium",
                    "description": f"Execute: {action}"
                })
            
            return actions
            
        except Exception as e:
            logger.error(f"Error planning actions for {self.name}: {e}")
            return [
                {
                    "action": "fallback_processing",
                    "tool": "internal_processing",
                    "priority": "high",
                    "description": "Execute fallback processing due to planning error"
                }
            ]
    
    async def _determine_tool_parameters(self, tool_name: str, task_input: str, 
                                       context: Dict[str, Any], reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Determine tool parameters based on agent reasoning."""
        
        # Use GROQ to determine optimal parameters
        parameter_prompt = f"""Based on the following context, determine the optimal parameters for the {tool_name} tool:

Task Input: {task_input}
Agent Reasoning: {reasoning.get('reasoning', '')}
Expected Outcome: {reasoning.get('expected_outcome', '')}

Provide parameters in JSON format suitable for the {tool_name} tool."""
        
        try:
            # For now, use simplified parameter determination
            # In production, this could use GROQ for more sophisticated parameter selection
            return await self._get_default_tool_parameters(tool_name, task_input, context)
            
        except Exception as e:
            logger.warning(f"Error determining parameters for {tool_name}: {e}")
            return await self._get_default_tool_parameters(tool_name, task_input, context)
    
    async def _get_default_tool_parameters(self, tool_name: str, task_input: str, 
                                         context: Dict[str, Any]) -> Dict[str, Any]:
        """Get default parameters for tools."""
        
        if tool_name == "web_search":
            # Extract search terms from task input
            search_query = task_input
            if len(search_query) > 100:
                # Use first sentence as query
                search_query = search_query.split('.')[0]
            
            return {
                "query": search_query,
                "max_results": 5
            }
        
        elif tool_name == "calculator":
            # Look for mathematical expressions
            import re
            math_expressions = re.findall(r'[\d+\-*/().%\s]+', task_input)
            expression = math_expressions[0].strip() if math_expressions else "1+1"
            
            return {"expression": expression}
        
        elif tool_name == "text_summarizer":
            return {
                "text": task_input,
                "max_sentences": 3
            }
        
        elif tool_name == "datetime_tool":
            return {"operation": "now"}
        
        elif tool_name == "json_parser":
            # Look for JSON content
            if "{" in task_input and "}" in task_input:
                start = task_input.find("{")
                end = task_input.rfind("}") + 1
                json_content = task_input[start:end]
                return {"json_data": json_content}
            else:
                return {"json_data": "{}"}
        
        elif tool_name == "http_request":
            # Look for URLs
            import re
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', task_input)
            url = urls[0] if urls else "https://httpbin.org/get"
            
            return {
                "url": url,
                "method": "GET"
            }
        
        else:
            return {"input": task_input}
    
    async def _validate_results(self, reasoning_result: Dict[str, Any], 
                              tool_results: List[Dict[str, Any]], 
                              original_task: str) -> Dict[str, Any]:
        """Validate results against success criteria."""
        
        validation = {
            "success": True,
            "criteria_met": [],
            "criteria_failed": [],
            "overall_score": 0.0,
            "validation_notes": []
        }
        
        # Check if tools executed successfully
        successful_tools = [r for r in tool_results if r.get("success", False)]
        total_tools = len(tool_results)
        
        if total_tools > 0:
            tool_success_rate = len(successful_tools) / total_tools
            validation["overall_score"] += tool_success_rate * 0.4
        else:
            validation["overall_score"] += 0.2  # Some credit for reasoning
        
        # Check confidence level
        confidence = reasoning_result.get("confidence_level", "medium")
        confidence_scores = {"high": 0.3, "medium": 0.2, "low": 0.1}
        validation["overall_score"] += confidence_scores.get(confidence, 0.1)
        
        # Check if reasoning is comprehensive
        reasoning_text = reasoning_result.get("reasoning", "")
        if len(reasoning_text) > 50:
            validation["overall_score"] += 0.2
            validation["criteria_met"].append("Comprehensive reasoning provided")
        else:
            validation["criteria_failed"].append("Reasoning too brief")
        
        # Check if actions were planned
        planned_actions = reasoning_result.get("planned_actions", [])
        if len(planned_actions) > 0:
            validation["overall_score"] += 0.1
            validation["criteria_met"].append("Actions planned")
        else:
            validation["criteria_failed"].append("No actions planned")
        
        # Overall success determination
        validation["success"] = validation["overall_score"] >= 0.6
        
        # Add validation notes
        if validation["success"]:
            validation["validation_notes"].append("Agent successfully completed the assigned task")
        else:
            validation["validation_notes"].append("Agent completed task but with some limitations")
        
        return validation
    
    def _synthesize_output(self, reasoning_result: Dict[str, Any], 
                          tool_results: List[Dict[str, Any]], 
                          validation_result: Dict[str, Any]) -> str:
        """Synthesize comprehensive output from all results."""
        
        output_parts = []
        
        # Add agent introduction
        output_parts.append(f"**{self.name}** ({self.specialization} specialist)")
        
        # Add reasoning summary
        reasoning = reasoning_result.get("reasoning", "")
        if reasoning:
            output_parts.append(f"**Analysis:** {reasoning}")
        
        # Add tool results summary
        successful_tools = [r for r in tool_results if r.get("success", False)]
        if successful_tools:
            output_parts.append("**Actions Taken:**")
            for tool_result in successful_tools:
                tool_name = tool_result["tool_name"]
                summary = self._summarize_tool_result(tool_result)
                output_parts.append(f"• {tool_name}: {summary}")
        
        # Add validation summary
        if validation_result["success"]:
            output_parts.append(f"**Result:** Task completed successfully (Score: {validation_result['overall_score']:.1f}/1.0)")
        else:
            output_parts.append(f"**Result:** Task completed with limitations (Score: {validation_result['overall_score']:.1f}/1.0)")
        
        # Add next steps if available
        next_steps = reasoning_result.get("next_steps", [])
        if next_steps:
            output_parts.append("**Recommended Next Steps:**")
            for step in next_steps:
                output_parts.append(f"• {step}")
        
        return "\n\n".join(output_parts)
    
    def _summarize_tool_result(self, tool_result: Dict[str, Any]) -> str:
        """Create summary of tool execution result."""
        
        if not tool_result.get("success", False):
            return f"Failed - {tool_result.get('error', 'Unknown error')}"
        
        result = tool_result.get("result", {})
        tool_name = tool_result["tool_name"]
        
        if tool_name == "web_search":
            total_results = result.get("total_results", 0)
            return f"Found {total_results} relevant search results"
        
        elif tool_name == "calculator":
            calc_result = result.get("result")
            return f"Calculated result: {calc_result}"
        
        elif tool_name == "text_summarizer":
            summary_length = result.get("summary_length", 0)
            return f"Created summary ({summary_length} characters)"
        
        elif tool_name == "datetime_tool":
            current_time = result.get("current_datetime", "")
            return f"Retrieved current time: {current_time[:19]}"
        
        elif tool_name == "json_parser":
            data_type = result.get("data_type", "unknown")
            return f"Parsed JSON data (type: {data_type})"
        
        elif tool_name == "http_request":
            status_code = result.get("status_code", 0)
            return f"HTTP request completed (status: {status_code})"
        
        else:
            return "Executed successfully"
    
    def get_agent_definition(self) -> Dict[str, Any]:
        """Get the original agent definition."""
        return self.agent_definition
    
    def update_specialization(self, new_specialization: str):
        """Update agent specialization based on performance."""
        self.specialization = new_specialization
        logger.info(f"Updated {self.name} specialization to: {new_specialization}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this dynamic agent."""
        
        if not self.execution_history:
            return {"no_executions": True}
        
        successful_executions = [e for e in self.execution_history if e["success"]]
        total_executions = len(self.execution_history)
        
        # Calculate tool usage statistics
        all_tools_used = []
        for execution in self.execution_history:
            all_tools_used.extend(execution.get("tools_used", []))
        
        tool_usage = {}
        for tool in all_tools_used:
            tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        return {
            "total_executions": total_executions,
            "successful_executions": len(successful_executions),
            "success_rate": len(successful_executions) / total_executions if total_executions > 0 else 0,
            "average_confidence": sum(
                1 if e.get("confidence") == "high" else 0.5 if e.get("confidence") == "medium" else 0
                for e in self.execution_history
            ) / total_executions if total_executions > 0 else 0,
            "most_used_tools": sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:3],
            "specialization": self.specialization,
            "preferred_tools": self.preferred_tools
        }
