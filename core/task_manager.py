"""Task manager for coordinating complex multi-step tasks in EUNA MVP."""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

from services.database_service import db_service
from services.memory_service import memory_service

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskManager:
    """Manager for coordinating and tracking task execution."""
    
    def __init__(self):
        self.task_dependencies: Dict[int, List[int]] = {}
        self.task_workflows: Dict[int, Dict[str, Any]] = {}
        self.task_timeouts: Dict[int, datetime] = {}
        self.max_concurrent_tasks = 10
    
    async def create_task_workflow(self, task_id: int, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create a workflow for task execution."""
        
        workflow = {
            "task_id": task_id,
            "definition": workflow_definition,
            "steps": workflow_definition.get("steps", []),
            "current_step": 0,
            "step_results": [],
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now(),
            "dependencies": workflow_definition.get("dependencies", []),
            "timeout_minutes": workflow_definition.get("timeout_minutes", 30)
        }
        
        self.task_workflows[task_id] = workflow
        
        # Set timeout
        timeout_time = datetime.now() + timedelta(minutes=workflow["timeout_minutes"])
        self.task_timeouts[task_id] = timeout_time
        
        # Record dependencies
        if workflow["dependencies"]:
            self.task_dependencies[task_id] = workflow["dependencies"]
        
        logger.info(f"Created workflow for task {task_id} with {len(workflow['steps'])} steps")
        
        return workflow
    
    async def execute_workflow_step(self, task_id: int, step_index: int, 
                                  agent_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific workflow step."""
        
        workflow = self.task_workflows.get(task_id)
        if not workflow:
            raise ValueError(f"Workflow not found for task {task_id}")
        
        if step_index >= len(workflow["steps"]):
            raise ValueError(f"Step index {step_index} out of range")
        
        step = workflow["steps"][step_index]
        step_result = {
            "step_index": step_index,
            "step_name": step.get("name", f"Step {step_index}"),
            "agent_result": agent_result,
            "executed_at": datetime.now(),
            "success": agent_result.get("success", False)
        }
        
        # Add step result to workflow
        workflow["step_results"].append(step_result)
        workflow["current_step"] = step_index + 1
        
        # Check if workflow is complete
        if workflow["current_step"] >= len(workflow["steps"]):
            workflow["status"] = TaskStatus.COMPLETED.value
            workflow["completed_at"] = datetime.now()
            
            # Store workflow result in memory
            await self._store_workflow_result(task_id, workflow)
        
        logger.info(f"Executed step {step_index} for task {task_id}: {step_result['success']}")
        
        return step_result
    
    async def check_task_dependencies(self, task_id: int) -> Dict[str, Any]:
        """Check if task dependencies are satisfied."""
        
        dependencies = self.task_dependencies.get(task_id, [])
        if not dependencies:
            return {"satisfied": True, "pending_dependencies": []}
        
        pending_dependencies = []
        
        for dep_task_id in dependencies:
            dep_task = await db_service.get_task(dep_task_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED.value:
                pending_dependencies.append(dep_task_id)
        
        return {
            "satisfied": len(pending_dependencies) == 0,
            "pending_dependencies": pending_dependencies,
            "total_dependencies": len(dependencies)
        }
    
    async def get_task_progress(self, task_id: int) -> Dict[str, Any]:
        """Get detailed progress information for a task."""
        
        workflow = self.task_workflows.get(task_id)
        if not workflow:
            # Get basic task info from database
            task = await db_service.get_task(task_id)
            if task:
                return {
                    "task_id": task_id,
                    "status": task.status,
                    "progress_percentage": 100 if task.status == TaskStatus.COMPLETED.value else 0,
                    "has_workflow": False
                }
            return {"error": f"Task {task_id} not found"}
        
        total_steps = len(workflow["steps"])
        completed_steps = len([r for r in workflow["step_results"] if r["success"]])
        failed_steps = len([r for r in workflow["step_results"] if not r["success"]])
        
        progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        # Check timeout
        is_timed_out = datetime.now() > self.task_timeouts.get(task_id, datetime.max)
        
        return {
            "task_id": task_id,
            "status": workflow["status"],
            "progress_percentage": progress_percentage,
            "current_step": workflow["current_step"],
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "step_results": workflow["step_results"],
            "has_workflow": True,
            "created_at": workflow["created_at"].isoformat(),
            "timeout_at": self.task_timeouts.get(task_id, datetime.max).isoformat(),
            "is_timed_out": is_timed_out,
            "estimated_completion": self._estimate_completion_time(workflow)
        }
    
    async def pause_task(self, task_id: int) -> Dict[str, Any]:
        """Pause task execution."""
        
        workflow = self.task_workflows.get(task_id)
        if workflow and workflow["status"] == TaskStatus.IN_PROGRESS.value:
            workflow["status"] = TaskStatus.PAUSED.value
            workflow["paused_at"] = datetime.now()
            
            await db_service.update_task_status(task_id, TaskStatus.PAUSED.value)
            
            return {"task_id": task_id, "status": "paused"}
        
        return {"error": f"Cannot pause task {task_id}"}
    
    async def resume_task(self, task_id: int) -> Dict[str, Any]:
        """Resume paused task execution."""
        
        workflow = self.task_workflows.get(task_id)
        if workflow and workflow["status"] == TaskStatus.PAUSED.value:
            workflow["status"] = TaskStatus.IN_PROGRESS.value
            workflow["resumed_at"] = datetime.now()
            
            await db_service.update_task_status(task_id, TaskStatus.IN_PROGRESS.value)
            
            return {"task_id": task_id, "status": "resumed"}
        
        return {"error": f"Cannot resume task {task_id}"}
    
    async def get_task_timeline(self, task_id: int) -> List[Dict[str, Any]]:
        """Get timeline of task execution events."""
        
        timeline = []
        
        # Get task logs from database
        logs = await db_service.get_task_logs(task_id)
        for log in logs:
            timeline.append({
                "timestamp": log.timestamp.isoformat(),
                "event_type": "log",
                "level": log.level,
                "message": log.message,
                "metadata": log.metadata
            })
        
        # Add workflow events if available
        workflow = self.task_workflows.get(task_id)
        if workflow:
            timeline.append({
                "timestamp": workflow["created_at"].isoformat(),
                "event_type": "workflow_created",
                "message": f"Workflow created with {len(workflow['steps'])} steps"
            })
            
            for step_result in workflow["step_results"]:
                timeline.append({
                    "timestamp": step_result["executed_at"].isoformat(),
                    "event_type": "step_completed",
                    "step_name": step_result["step_name"],
                    "success": step_result["success"],
                    "message": f"Step '{step_result['step_name']}' {'completed' if step_result['success'] else 'failed'}"
                })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        
        return timeline
    
    async def optimize_task_scheduling(self) -> Dict[str, Any]:
        """Optimize scheduling of pending tasks based on dependencies and priorities."""
        
        # Get all pending tasks
        pending_tasks = await db_service.get_recent_tasks(limit=100)
        pending_tasks = [t for t in pending_tasks if t.status == TaskStatus.PENDING.value]
        
        # Create scheduling plan
        scheduling_plan = {
            "immediate_execution": [],
            "dependency_waiting": [],
            "resource_limited": [],
            "recommendations": []
        }
        
        for task in pending_tasks:
            task_id = task.id
            
            # Check dependencies
            dep_check = await self.check_task_dependencies(task_id)
            
            if dep_check["satisfied"]:
                if len(scheduling_plan["immediate_execution"]) < self.max_concurrent_tasks:
                    scheduling_plan["immediate_execution"].append({
                        "task_id": task_id,
                        "priority": task.priority,
                        "created_at": task.created_at.isoformat()
                    })
                else:
                    scheduling_plan["resource_limited"].append({
                        "task_id": task_id,
                        "priority": task.priority,
                        "reason": "Max concurrent tasks reached"
                    })
            else:
                scheduling_plan["dependency_waiting"].append({
                    "task_id": task_id,
                    "pending_dependencies": dep_check["pending_dependencies"]
                })
        
        # Add recommendations
        if len(scheduling_plan["resource_limited"]) > 0:
            scheduling_plan["recommendations"].append(
                "Consider increasing max_concurrent_tasks to handle more tasks simultaneously"
            )
        
        if len(scheduling_plan["dependency_waiting"]) > 0:
            scheduling_plan["recommendations"].append(
                "Some tasks are waiting for dependencies - check if dependent tasks need attention"
            )
        
        return scheduling_plan
    
    def _estimate_completion_time(self, workflow: Dict[str, Any]) -> Optional[str]:
        """Estimate when the workflow will complete."""
        
        if workflow["status"] == TaskStatus.COMPLETED.value:
            return workflow.get("completed_at", datetime.now()).isoformat()
        
        completed_steps = len([r for r in workflow["step_results"] if r["success"]])
        total_steps = len(workflow["steps"])
        
        if completed_steps == 0:
            return None
        
        # Calculate average time per step
        step_times = []
        for i, result in enumerate(workflow["step_results"]):
            if i == 0:
                start_time = workflow["created_at"]
            else:
                start_time = workflow["step_results"][i-1]["executed_at"]
            
            duration = (result["executed_at"] - start_time).total_seconds()
            step_times.append(duration)
        
        if step_times:
            avg_step_time = sum(step_times) / len(step_times)
            remaining_steps = total_steps - completed_steps
            estimated_remaining_seconds = remaining_steps * avg_step_time
            
            estimated_completion = datetime.now() + timedelta(seconds=estimated_remaining_seconds)
            return estimated_completion.isoformat()
        
        return None
    
    async def _store_workflow_result(self, task_id: int, workflow: Dict[str, Any]):
        """Store completed workflow result in memory."""
        
        workflow_summary = {
            "task_id": task_id,
            "total_steps": len(workflow["steps"]),
            "successful_steps": len([r for r in workflow["step_results"] if r["success"]]),
            "execution_time": (workflow["completed_at"] - workflow["created_at"]).total_seconds(),
            "step_results": workflow["step_results"]
        }
        
        await memory_service.store_memory(
            content=f"Workflow completed for task {task_id}: {workflow_summary}",
            content_type="workflow_result",
            metadata=workflow_summary,
            task_id=task_id
        )
    
    async def cleanup_completed_workflows(self, older_than_hours: int = 24):
        """Clean up old completed workflows to free memory."""
        
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        workflows_to_remove = []
        for task_id, workflow in self.task_workflows.items():
            if (workflow["status"] == TaskStatus.COMPLETED.value and 
                workflow.get("completed_at", datetime.now()) < cutoff_time):
                workflows_to_remove.append(task_id)
        
        for task_id in workflows_to_remove:
            del self.task_workflows[task_id]
            if task_id in self.task_timeouts:
                del self.task_timeouts[task_id]
            if task_id in self.task_dependencies:
                del self.task_dependencies[task_id]
        
        logger.info(f"Cleaned up {len(workflows_to_remove)} completed workflows")
        
        return {"cleaned_workflows": len(workflows_to_remove)}


# Global task manager instance
task_manager = TaskManager()
