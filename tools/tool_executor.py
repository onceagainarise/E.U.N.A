"""Tool execution engine for EUNA MVP."""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from tools.tool_registry import tool_registry
from services.database_service import db_service

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Engine for executing tools and managing tool workflows."""
    
    def __init__(self):
        self.active_executions: Dict[str, Dict] = {}
        self.execution_history: List[Dict] = []
    
    async def execute_single_tool(self, agent_id: int, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool for an agent."""
        
        execution_id = f"{agent_id}_{tool_name}_{datetime.now().timestamp()}"
        
        # Record execution start
        execution_record = {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "started_at": datetime.now(),
            "status": "running"
        }
        
        self.active_executions[execution_id] = execution_record
        
        try:
            # Create database record
            db_execution = await db_service.create_agent_execution(
                agent_id=agent_id,
                action=f"execute_tool_{tool_name}",
                input_data={"tool": tool_name, "parameters": parameters}
            )
            
            # Execute tool
            logger.info(f"Executing tool {tool_name} for agent {agent_id}")
            result = await tool_registry.execute_tool(tool_name, **parameters)
            
            # Update execution record
            execution_record.update({
                "completed_at": datetime.now(),
                "status": "completed" if result["success"] else "failed",
                "result": result,
                "duration": (datetime.now() - execution_record["started_at"]).total_seconds()
            })
            
            # Update database
            await db_service.update_agent_execution(
                execution_id=db_execution.id,
                status=execution_record["status"],
                output_data=result,
                tools_used=[tool_name],
                error_message=result.get("error") if not result["success"] else None
            )
            
            # Move to history
            self.execution_history.append(execution_record)
            del self.active_executions[execution_id]
            
            logger.info(f"Tool {tool_name} execution completed: {result['success']}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            
            # Update execution record
            execution_record.update({
                "completed_at": datetime.now(),
                "status": "error",
                "error": str(e),
                "duration": (datetime.now() - execution_record["started_at"]).total_seconds()
            })
            
            # Move to history
            self.execution_history.append(execution_record)
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            return {
                "success": False,
                "tool_name": tool_name,
                "result": None,
                "error": str(e)
            }
    
    async def execute_tool_workflow(self, agent_id: int, workflow: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a workflow of tools in sequence."""
        
        results = []
        workflow_context = {}
        
        logger.info(f"Starting tool workflow for agent {agent_id} with {len(workflow)} steps")
        
        for step_index, step in enumerate(workflow):
            tool_name = step.get("tool")
            parameters = step.get("parameters", {})
            condition = step.get("condition")
            
            # Check condition if specified
            if condition and not self._evaluate_condition(condition, workflow_context):
                logger.info(f"Skipping step {step_index}: condition not met")
                results.append({
                    "step": step_index,
                    "tool": tool_name,
                    "skipped": True,
                    "reason": "condition_not_met"
                })
                continue
            
            # Replace context variables in parameters
            resolved_parameters = self._resolve_context_variables(parameters, workflow_context)
            
            # Execute tool
            result = await self.execute_single_tool(agent_id, tool_name, resolved_parameters)
            
            # Add step info to result
            result.update({
                "step": step_index,
                "workflow_position": f"{step_index + 1}/{len(workflow)}"
            })
            
            results.append(result)
            
            # Update workflow context
            if result["success"]:
                workflow_context[f"step_{step_index}_result"] = result["result"]
                workflow_context[f"{tool_name}_result"] = result["result"]
            
            # Stop workflow if tool failed and no error handling specified
            if not result["success"] and not step.get("continue_on_error", False):
                logger.warning(f"Workflow stopped at step {step_index} due to tool failure")
                break
            
            # Add delay if specified
            delay = step.get("delay_seconds", 0)
            if delay > 0:
                await asyncio.sleep(delay)
        
        logger.info(f"Tool workflow completed for agent {agent_id}: {len(results)} steps executed")
        return results
    
    async def execute_parallel_tools(self, agent_id: int, tool_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple tools in parallel."""
        
        logger.info(f"Starting parallel tool execution for agent {agent_id}: {len(tool_specs)} tools")
        
        # Create tasks for parallel execution
        tasks = []
        for spec in tool_specs:
            tool_name = spec.get("tool")
            parameters = spec.get("parameters", {})
            task = asyncio.create_task(
                self.execute_single_tool(agent_id, tool_name, parameters)
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "tool_name": tool_specs[i].get("tool"),
                    "result": None,
                    "error": str(result),
                    "parallel_index": i
                })
            else:
                result["parallel_index"] = i
                processed_results.append(result)
        
        logger.info(f"Parallel tool execution completed for agent {agent_id}")
        return processed_results
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string against the workflow context."""
        
        try:
            # Simple condition evaluation (can be extended)
            # Supports conditions like: "step_0_result.success == True"
            
            # Replace context variables
            resolved_condition = condition
            for key, value in context.items():
                if key in resolved_condition:
                    resolved_condition = resolved_condition.replace(f"{key}", str(value))
            
            # Basic safety check
            allowed_operators = ["==", "!=", "and", "or", "True", "False", "None"]
            if any(op in resolved_condition for op in ["import", "exec", "eval", "__"]):
                logger.warning(f"Unsafe condition detected: {condition}")
                return False
            
            # Evaluate condition
            return eval(resolved_condition, {"__builtins__": {}})
            
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    def _resolve_context_variables(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve context variables in parameters."""
        
        resolved = {}
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("$context."):
                context_key = value[9:]  # Remove "$context."
                resolved[key] = context.get(context_key, value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_context_variables(value, context)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_context_variables(item, context) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def get_execution_status(self, agent_id: Optional[int] = None) -> Dict[str, Any]:
        """Get current execution status."""
        
        active_executions = list(self.active_executions.values())
        if agent_id:
            active_executions = [ex for ex in active_executions if ex["agent_id"] == agent_id]
        
        recent_history = self.execution_history[-20:]  # Last 20 executions
        if agent_id:
            recent_history = [ex for ex in recent_history if ex["agent_id"] == agent_id]
        
        return {
            "active_executions": len(active_executions),
            "active_details": active_executions,
            "recent_executions": len(recent_history),
            "recent_details": recent_history,
            "total_executions": len(self.execution_history)
        }
    
    def get_tool_usage_stats(self) -> Dict[str, Any]:
        """Get statistics about tool usage."""
        
        tool_counts = {}
        success_counts = {}
        error_counts = {}
        
        for execution in self.execution_history:
            tool_name = execution.get("tool_name", "unknown")
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            
            if execution.get("status") == "completed":
                success_counts[tool_name] = success_counts.get(tool_name, 0) + 1
            elif execution.get("status") in ["failed", "error"]:
                error_counts[tool_name] = error_counts.get(tool_name, 0) + 1
        
        return {
            "tool_usage_counts": tool_counts,
            "success_counts": success_counts,
            "error_counts": error_counts,
            "success_rates": {
                tool: success_counts.get(tool, 0) / tool_counts[tool]
                for tool in tool_counts
            }
        }


# Global tool executor instance
tool_executor = ToolExecutor()
