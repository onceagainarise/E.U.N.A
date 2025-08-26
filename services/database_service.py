"""Database service for EUNA MVP."""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

from config.settings import settings
from database.models import Base, Task, Agent, AgentExecution, TaskLog, UserSession, MemoryEntry

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service for managing SQLite operations."""
    
    def __init__(self):
        self.engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # Task operations
    async def create_task(self, user_input: str, priority: str = "medium") -> Task:
        """Create a new task."""
        with self.get_session() as session:
            task = Task(user_input=user_input, priority=priority, status="pending")
            session.add(task)
            session.flush()
            session.refresh(task)
            logger.info(f"Created task {task.id}: {user_input[:50]}...")
            return task
    
    async def get_task(self, task_id: int) -> Optional[Task]:
        """Get task by ID."""
        with self.get_session() as session:
            return session.get(Task, task_id)
    
    async def update_task_status(self, task_id: int, status: str, result: Optional[Dict] = None, error_message: Optional[str] = None):
        """Update task status and result."""
        with self.get_session() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = status
                if result:
                    task.result = result
                if error_message:
                    task.error_message = error_message
                if status == "completed":
                    from datetime import datetime
                    task.completed_at = datetime.utcnow()
                logger.info(f"Updated task {task_id} status to {status}")
    
    async def get_recent_tasks(self, limit: int = 10) -> List[Task]:
        """Get recent tasks."""
        with self.get_session() as session:
            stmt = select(Task).order_by(Task.created_at.desc()).limit(limit)
            return list(session.execute(stmt).scalars())
    
    # Agent operations
    async def create_agent(self, task_id: int, name: str, agent_type: str, role: str, 
                          capabilities: Optional[Dict] = None, prompt_template: Optional[str] = None) -> Agent:
        """Create a new agent."""
        with self.get_session() as session:
            agent = Agent(
                task_id=task_id,
                name=name,
                agent_type=agent_type,
                role=role,
                capabilities=capabilities,
                prompt_template=prompt_template
            )
            session.add(agent)
            session.flush()
            session.refresh(agent)
            logger.info(f"Created agent {agent.id}: {name}")
            return agent
    
    async def get_task_agents(self, task_id: int) -> List[Agent]:
        """Get all agents for a task."""
        with self.get_session() as session:
            stmt = select(Agent).where(Agent.task_id == task_id)
            return list(session.execute(stmt).scalars())
    
    async def update_agent_status(self, agent_id: int, status: str):
        """Update agent status."""
        with self.get_session() as session:
            agent = session.get(Agent, agent_id)
            if agent:
                agent.status = status
                if status == "completed":
                    from datetime import datetime
                    agent.completed_at = datetime.utcnow()
                logger.info(f"Updated agent {agent_id} status to {status}")
    
    # Agent execution operations
    async def create_agent_execution(self, agent_id: int, action: str, input_data: Optional[Dict] = None) -> AgentExecution:
        """Create a new agent execution."""
        with self.get_session() as session:
            execution = AgentExecution(
                agent_id=agent_id,
                action=action,
                input_data=input_data,
                status="pending"
            )
            session.add(execution)
            session.flush()
            session.refresh(execution)
            return execution
    
    async def update_agent_execution(self, execution_id: int, status: str, 
                                   output_data: Optional[Dict] = None, 
                                   tools_used: Optional[List[str]] = None,
                                   error_message: Optional[str] = None):
        """Update agent execution."""
        with self.get_session() as session:
            execution = session.get(AgentExecution, execution_id)
            if execution:
                execution.status = status
                if output_data:
                    execution.output_data = output_data
                if tools_used:
                    execution.tools_used = tools_used
                if error_message:
                    execution.error_message = error_message
                if status in ["completed", "failed"]:
                    from datetime import datetime
                    execution.completed_at = datetime.utcnow()
    
    # Logging operations
    async def add_task_log(self, task_id: int, level: str, message: str, metadata: Optional[Dict] = None):
        """Add a log entry for a task."""
        with self.get_session() as session:
            log_entry = TaskLog(
                task_id=task_id,
                level=level,
                message=message,
                metadata=metadata
            )
            session.add(log_entry)
            logger.debug(f"Added log for task {task_id}: {message}")
    
    async def get_task_logs(self, task_id: int) -> List[TaskLog]:
        """Get all logs for a task."""
        with self.get_session() as session:
            stmt = select(TaskLog).where(TaskLog.task_id == task_id).order_by(TaskLog.timestamp)
            return list(session.execute(stmt).scalars())
    
    # Session operations
    async def create_or_update_session(self, session_id: str, user_preferences: Optional[Dict] = None, 
                                     context_data: Optional[Dict] = None) -> UserSession:
        """Create or update user session."""
        with self.get_session() as session:
            user_session = session.query(UserSession).filter(UserSession.session_id == session_id).first()
            if user_session:
                if user_preferences:
                    user_session.user_preferences = user_preferences
                if context_data:
                    user_session.context_data = context_data
                from datetime import datetime
                user_session.last_activity = datetime.utcnow()
            else:
                user_session = UserSession(
                    session_id=session_id,
                    user_preferences=user_preferences,
                    context_data=context_data
                )
                session.add(user_session)
            session.flush()
            session.refresh(user_session)
            return user_session
    
    # Memory operations
    async def create_memory_entry(self, content: str, content_type: str, 
                                metadata: Optional[Dict] = None, embedding_id: Optional[str] = None) -> MemoryEntry:
        """Create a new memory entry."""
        with self.get_session() as session:
            memory_entry = MemoryEntry(
                content=content,
                content_type=content_type,
                metadata=metadata,
                embedding_id=embedding_id
            )
            session.add(memory_entry)
            session.flush()
            session.refresh(memory_entry)
            return memory_entry
    
    async def get_memory_entries(self, content_type: Optional[str] = None, limit: int = 50) -> List[MemoryEntry]:
        """Get memory entries."""
        with self.get_session() as session:
            stmt = select(MemoryEntry)
            if content_type:
                stmt = stmt.where(MemoryEntry.content_type == content_type)
            stmt = stmt.order_by(MemoryEntry.relevance_score.desc(), MemoryEntry.created_at.desc()).limit(limit)
            return list(session.execute(stmt).scalars())


# Global database service instance
db_service = DatabaseService()
