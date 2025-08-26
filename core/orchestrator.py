"""Master orchestrator for EUNA MVP."""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from services.database_service import db_service
from services.groq_service import groq_service
from services.memory_service import memory_service
from tools.tool_executor import tool_executor
from core.agent_factory import agent_factory

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    """Master orchestrator that coordinates agents and manages task execution."""
    
    def __init__(self):
        self.active_tasks: Dict[int, Dict] = {}
        self.task_queue: List[Dict] = []
        self.max_concurrent_tasks = 5
    
    async def submit_task(self, user_input: str, session_id: Optional[str] = None, 
                         priority: str = "medium") -> Dict[str, Any]:
        """Submit a new task for processing."""
        
        try:
            # Create task in database
            task = await db_service.create_task(user_input, priority)
            task_id = task.id
            
            # Log task submission
            await db_service.add_task_log(
                task_id=task_id,
                level="INFO",
                message=f"Task submitted: {user_input[:100]}...",
                metadata={"session_id": session_id}
            )
            
            # Get context from memory
            context = await memory_service.get_context_for_task(user_input, task_id)
            
            # Analyze task using GROQ
            logger.info(f"Analyzing task {task_id}")
            task_analysis = await groq_service.analyze_task(user_input, context)
            
            # Create task execution plan
            execution_plan = {
                "task_id": task_id,
                "user_input": user_input,
                "analysis": task_analysis,
                "context": context,
                "session_id": session_id,
                "status": "pending",
                "created_at": datetime.now(),
                "agents": [],
                "results": []
            }
            
            # Add to active tasks
            self.active_tasks[task_id] = execution_plan
            
            # Start task execution asynchronously
            asyncio.create_task(self._execute_task(task_id))
            
            logger.info(f"Task {task_id} submitted and queued for execution")
            
            return {
                "task_id": task_id,
                "status": "submitted",
                "analysis": task_analysis,
                "estimated_duration": task_analysis.get("estimated_duration", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Error submitting task: {e}")
            raise
    
    async def _execute_task(self, task_id: int):
        """Execute a task using the orchestrated agent approach."""
        
        execution_plan = self.active_tasks.get(task_id)
        if not execution_plan:
            logger.error(f"Task {task_id} not found in active tasks")
            return
        
        try:
            # Update task status
            await db_service.update_task_status(task_id, "in_progress")
            execution_plan["status"] = "in_progress"
            
            await db_service.add_task_log(
                task_id=task_id,
                level="INFO",
                message="Task execution started"
            )
            
            # Create agents based on analysis
            agents = await self._create_agents_for_task(task_id, execution_plan)
            execution_plan["agents"] = agents
            
            # Execute agents
            agent_results = await self._execute_agents(task_id, agents)
            execution_plan["results"] = agent_results
            
            # Synthesize final result
            final_result = await groq_service.synthesize_results(
                agent_results, execution_plan["user_input"]
            )
            
            # Store result and update status
            await db_service.update_task_status(
                task_id, "completed", result=final_result
            )
            execution_plan["status"] = "completed"
            execution_plan["final_result"] = final_result
            
            # Store in memory for future reference
            await memory_service.store_task_result(
                task_id, execution_plan["user_input"], final_result
            )
            
            await db_service.add_task_log(
                task_id=task_id,
                level="INFO",
                message="Task execution completed successfully",
                metadata={"confidence_score": final_result.get("confidence_score")}
            )
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            
            # Update task with error
            await db_service.update_task_status(
                task_id, "failed", error_message=str(e)
            )
            execution_plan["status"] = "failed"
            execution_plan["error"] = str(e)
            
            await db_service.add_task_log(
                task_id=task_id,
                level="ERROR",
                message=f"Task execution failed: {str(e)}"
            )
        
        finally:
            # Clean up active task after some time
            await asyncio.sleep(300)  # Keep for 5 minutes
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    async def _create_agents_for_task(self, task_id: int, execution_plan: Dict) -> List[Dict]:
        """Create agents based on task analysis."""
        
        analysis = execution_plan["analysis"]
        suggested_agents = analysis.get("suggested_agents", [])
        
        agents = []
        
        for agent_spec in suggested_agents:
            try:
                if agent_spec.get("type") == "dynamic":
                    # Create dynamic agent
                    agent_definition = await groq_service.generate_dynamic_agent(
                        agent_spec, execution_plan["user_input"]
                    )
                    
                    agent = await agent_factory.create_dynamic_agent(
                        task_id=task_id,
                        agent_definition=agent_definition
                    )
                else:
                    # Create default agent
                    agent = await agent_factory.create_default_agent(
                        task_id=task_id,
                        agent_type=agent_spec.get("name", "GeneralAgent"),
                        role=agent_spec.get("role", "General task processing")
                    )
                
                agents.append(agent)
                
                await db_service.add_task_log(
                    task_id=task_id,
                    level="INFO",
                    message=f"Created agent: {agent['name']} ({agent['type']})"
                )
                
            except Exception as e:
                logger.error(f"Error creating agent {agent_spec.get('name')}: {e}")
                await db_service.add_task_log(
                    task_id=task_id,
                    level="WARNING",
                    message=f"Failed to create agent {agent_spec.get('name')}: {str(e)}"
                )
        
        return agents
    
    async def _execute_agents(self, task_id: int, agents: List[Dict]) -> List[Dict]:
        """Execute all agents for a task."""
        
        agent_results = []
        
        # Determine execution strategy based on agent dependencies
        high_priority_agents = [a for a in agents if a.get("priority") == "high"]
        other_agents = [a for a in agents if a.get("priority") != "high"]
        
        # Execute high priority agents first
        for agent in high_priority_agents:
            result = await self._execute_single_agent(task_id, agent)
            agent_results.append(result)
        
        # Execute remaining agents (can be parallel for independent agents)
        if other_agents:
            if len(other_agents) == 1:
                result = await self._execute_single_agent(task_id, other_agents[0])
                agent_results.append(result)
            else:
                # Execute in parallel
                tasks = [
                    self._execute_single_agent(task_id, agent)
                    for agent in other_agents
                ]
                parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in parallel_results:
                    if isinstance(result, Exception):
                        agent_results.append({
                            "success": False,
                            "error": str(result),
                            "agent_name": "unknown"
                        })
                    else:
                        agent_results.append(result)
        
        return agent_results
    
    async def _execute_single_agent(self, task_id: int, agent: Dict) -> Dict[str, Any]:
        """Execute a single agent."""
        
        try:
            agent_id = agent["id"]
            agent_name = agent["name"]
            
            await db_service.add_task_log(
                task_id=task_id,
                level="INFO",
                message=f"Executing agent: {agent_name}"
            )
            
            # Get task details
            task = await db_service.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # Execute agent using agent factory
            result = await agent_factory.execute_agent(
                agent_id=agent_id,
                task_input=task.user_input,
                context=self.active_tasks[task_id].get("context", {})
            )
            
            await db_service.add_task_log(
                task_id=task_id,
                level="INFO",
                message=f"Agent {agent_name} completed: {result.get('success', False)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing agent {agent.get('name', 'unknown')}: {e}")
            
            await db_service.add_task_log(
                task_id=task_id,
                level="ERROR",
                message=f"Agent execution failed: {str(e)}"
            )
            
            return {
                "success": False,
                "agent_name": agent.get("name", "unknown"),
                "error": str(e)
            }
    
    async def get_task_status(self, task_id: int) -> Dict[str, Any]:
        """Get current status of a task."""
        
        # Check active tasks first
        if task_id in self.active_tasks:
            execution_plan = self.active_tasks[task_id]
            
            # Get latest database info
            task = await db_service.get_task(task_id)
            agents = await db_service.get_task_agents(task_id)
            logs = await db_service.get_task_logs(task_id)
            
            return {
                "task_id": task_id,
                "status": execution_plan["status"],
                "user_input": execution_plan["user_input"],
                "analysis": execution_plan.get("analysis", {}),
                "agents": [
                    {
                        "name": agent.name,
                        "type": agent.agent_type,
                        "status": agent.status,
                        "role": agent.role
                    }
                    for agent in agents
                ],
                "progress": {
                    "total_agents": len(agents),
                    "completed_agents": len([a for a in agents if a.status == "completed"]),
                    "failed_agents": len([a for a in agents if a.status == "failed"])
                },
                "final_result": execution_plan.get("final_result"),
                "logs": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "level": log.level,
                        "message": log.message
                    }
                    for log in logs[-10:]  # Last 10 logs
                ],
                "created_at": task.created_at.isoformat() if task else None,
                "updated_at": task.updated_at.isoformat() if task else None
            }
        
        # Check database for completed tasks
        task = await db_service.get_task(task_id)
        if task:
            agents = await db_service.get_task_agents(task_id)
            logs = await db_service.get_task_logs(task_id)
            
            return {
                "task_id": task_id,
                "status": task.status,
                "user_input": task.user_input,
                "result": task.result,
                "error_message": task.error_message,
                "agents": [
                    {
                        "name": agent.name,
                        "type": agent.agent_type,
                        "status": agent.status,
                        "role": agent.role
                    }
                    for agent in agents
                ],
                "logs": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "level": log.level,
                        "message": log.message
                    }
                    for log in logs
                ],
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
        
        return {"error": f"Task {task_id} not found"}
    
    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get all currently active agents."""
        
        active_agents = []
        
        for task_id, execution_plan in self.active_tasks.items():
            if execution_plan["status"] == "in_progress":
                agents = await db_service.get_task_agents(task_id)
                for agent in agents:
                    if agent.status == "active":
                        active_agents.append({
                            "agent_id": agent.id,
                            "task_id": task_id,
                            "name": agent.name,
                            "type": agent.agent_type,
                            "role": agent.role,
                            "created_at": agent.created_at.isoformat()
                        })
        
        return active_agents
    
    async def cancel_task(self, task_id: int) -> Dict[str, Any]:
        """Cancel a running task."""
        
        if task_id in self.active_tasks:
            execution_plan = self.active_tasks[task_id]
            execution_plan["status"] = "cancelled"
            
            # Update database
            await db_service.update_task_status(task_id, "cancelled")
            
            # Update agents
            agents = await db_service.get_task_agents(task_id)
            for agent in agents:
                if agent.status == "active":
                    await db_service.update_agent_status(agent.id, "cancelled")
            
            await db_service.add_task_log(
                task_id=task_id,
                level="WARNING",
                message="Task cancelled by user"
            )
            
            return {"task_id": task_id, "status": "cancelled"}
        
        return {"error": f"Task {task_id} not found or not active"}


# Global orchestrator instance
orchestrator = TaskOrchestrator()
