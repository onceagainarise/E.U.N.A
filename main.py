"""FastAPI main application for EUNA MVP."""

import logging
import asyncio
import json
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config.settings import settings
from core.orchestrator import orchestrator
from core.agent_factory import agent_factory
from tools.tool_registry import tool_registry
from tools.default_tools import register_default_tools
from services.database_service import db_service
from services.memory_service import memory_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

# Pydantic models for API
class TaskSubmissionRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None
    priority: str = "medium"

class TaskResponse(BaseModel):
    task_id: int
    status: str
    analysis: Optional[Dict[str, Any]] = None
    estimated_duration: Optional[str] = None

class AgentCreationRequest(BaseModel):
    task_id: int
    agent_type: str
    role: str
    capabilities: Optional[List[str]] = None

class TaskStatusResponse(BaseModel):
    task_id: int
    status: str
    user_input: str
    progress: Optional[Dict[str, Any]] = None
    final_result: Optional[Dict[str, Any]] = None
    agents: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting EUNA MVP application...")
    
    # Register default tools
    register_default_tools(tool_registry)
    logger.info("Registered default tools")
    
    # Initialize services
    try:
        # Test database connection
        async with db_service.get_session() as session:
            logger.info("Database connection established")
        
        # Initialize memory service
        logger.info("Memory service initialized")
        
        logger.info("EUNA MVP application started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down EUNA MVP application...")

# Create FastAPI app
app = FastAPI(
    title="EUNA MVP",
    description="Evolvable Unified Neural Agent - MVP Implementation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "EUNA MVP API",
        "version": "1.0.0",
        "description": "Evolvable Unified Neural Agent - MVP Implementation",
        "endpoints": {
            "submit_task": "POST /api/v1/tasks/submit",
            "get_task_status": "GET /api/v1/tasks/{task_id}",
            "list_active_agents": "GET /api/v1/agents/active",
            "create_agent": "POST /api/v1/agents/create",
            "websocket_updates": "WS /ws/task-updates"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        async with db_service.get_session() as session:
            pass
        
        return {
            "status": "healthy",
            "database": "connected",
            "active_tasks": len(orchestrator.active_tasks),
            "registered_tools": len(tool_registry.tools)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/api/v1/tasks/submit", response_model=TaskResponse)
async def submit_task(request: TaskSubmissionRequest, background_tasks: BackgroundTasks):
    """Submit a new task for processing."""
    try:
        logger.info(f"Received task submission: {request.user_input[:100]}...")
        
        result = await orchestrator.submit_task(
            user_input=request.user_input,
            session_id=request.session_id,
            priority=request.priority
        )
        
        # Broadcast task submission to WebSocket clients
        background_tasks.add_task(
            manager.broadcast,
            json.dumps({
                "type": "task_submitted",
                "task_id": result["task_id"],
                "status": result["status"]
            })
        )
        
        return TaskResponse(**result)
        
    except Exception as e:
        logger.error(f"Error submitting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: int):
    """Get status and details of a specific task."""
    try:
        result = await orchestrator.get_task_status(task_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tasks")
async def list_recent_tasks(limit: int = 10):
    """List recent tasks."""
    try:
        tasks = await db_service.get_recent_tasks(limit=limit)
        
        return {
            "tasks": [
                {
                    "task_id": task.id,
                    "user_input": task.user_input[:100] + "..." if len(task.user_input) > 100 else task.user_input,
                    "status": task.status,
                    "priority": task.priority,
                    "created_at": task.created_at.isoformat(),
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None
                }
                for task in tasks
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents/active")
async def get_active_agents():
    """Get list of currently active agents."""
    try:
        agents = await orchestrator.get_active_agents()
        return {"active_agents": agents}
        
    except Exception as e:
        logger.error(f"Error getting active agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/agents/create")
async def create_agent(request: AgentCreationRequest):
    """Manually create an agent for a task."""
    try:
        if request.agent_type in ["SummarizerAgent", "SearchAgent", "CodingAgent", "SchedulerAgent"]:
            agent = await agent_factory.create_default_agent(
                task_id=request.task_id,
                agent_type=request.agent_type,
                role=request.role
            )
        else:
            # Create dynamic agent
            agent_definition = {
                "name": request.agent_type,
                "role": request.role,
                "capabilities": request.capabilities or ["general_reasoning"],
                "system_prompt": f"You are a {request.agent_type} agent. {request.role}",
                "preferred_tools": ["web_search", "calculator"],
                "specialization": "Custom"
            }
            
            agent = await agent_factory.create_dynamic_agent(
                task_id=request.task_id,
                agent_definition=agent_definition
            )
        
        return {
            "success": True,
            "agent": agent
        }
        
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tools")
async def list_tools():
    """List available tools."""
    try:
        tools = tool_registry.list_tools()
        categories = {}
        
        for category, tool_names in tool_registry.tool_categories.items():
            categories[category] = [
                {
                    "name": name,
                    "description": tools[name]["description"],
                    "parameters": tools[name]["parameters"]
                }
                for name in tool_names if name in tools
            ]
        
        return {
            "total_tools": len(tools),
            "categories": categories
        }
        
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agent-types")
async def list_agent_types():
    """List available agent types."""
    try:
        agent_types = await agent_factory.list_available_agent_types()
        return {"agent_types": agent_types}
        
    except Exception as e:
        logger.error(f"Error listing agent types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/tasks/{task_id}")
async def cancel_task(task_id: int):
    """Cancel a running task."""
    try:
        result = await orchestrator.cancel_task(task_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/memory/search")
async def search_memory(query: str, content_type: Optional[str] = None, limit: int = 5):
    """Search memory for relevant information."""
    try:
        results = await memory_service.search_memory(
            query=query,
            content_type=content_type,
            limit=limit
        )
        
        return {
            "query": query,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/stats")
async def get_system_stats():
    """Get system statistics."""
    try:
        # Get task statistics
        recent_tasks = await db_service.get_recent_tasks(limit=100)
        completed_tasks = [t for t in recent_tasks if t.status == "completed"]
        failed_tasks = [t for t in recent_tasks if t.status == "failed"]
        
        # Get tool usage stats
        from tools.tool_executor import tool_executor
        tool_stats = tool_executor.get_tool_usage_stats()
        
        return {
            "tasks": {
                "total_recent": len(recent_tasks),
                "completed": len(completed_tasks),
                "failed": len(failed_tasks),
                "success_rate": len(completed_tasks) / len(recent_tasks) if recent_tasks else 0,
                "active": len(orchestrator.active_tasks)
            },
            "tools": {
                "registered": len(tool_registry.tools),
                "usage_stats": tool_stats
            },
            "agents": {
                "active": len(await orchestrator.get_active_agents())
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/ws/task-updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time task updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()
            
            # Echo back for now (can be extended for client commands)
            await manager.send_personal_message(f"Received: {data}", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint not found", "detail": str(exc)}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "detail": "An unexpected error occurred"}

# Main execution
if __name__ == "__main__":
    logger.info("Starting EUNA MVP server...")
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
