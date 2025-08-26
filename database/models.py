"""Database models for EUNA MVP."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Task(Base):
    """Task model for tracking user requests and their execution."""
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_input = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    priority = Column(String(20), default="medium")  # low, medium, high
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    agents = relationship("Agent", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")


class Agent(Base):
    """Agent model for tracking created agents and their capabilities."""
    
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    name = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)  # default, dynamic
    role = Column(String(200), nullable=False)
    capabilities = Column(JSON, nullable=True)
    prompt_template = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    task = relationship("Task", back_populates="agents")
    executions = relationship("AgentExecution", back_populates="agent", cascade="all, delete-orphan")


class AgentExecution(Base):
    """Agent execution model for tracking individual agent actions."""
    
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    action = Column(String(100), nullable=False)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    tools_used = Column(JSON, nullable=True)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="executions")


class TaskLog(Base):
    """Task log model for detailed execution tracking."""
    
    __tablename__ = "task_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    level = Column(String(20), default="INFO")  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="logs")


class UserSession(Base):
    """User session model for context management."""
    
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False)
    user_preferences = Column(JSON, nullable=True)
    context_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class MemoryEntry(Base):
    """Memory entry model for storing contextual information."""
    
    __tablename__ = "memory_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False)  # task_result, user_preference, learned_pattern
    metadata = Column(JSON, nullable=True)
    embedding_id = Column(String(100), nullable=True)  # Pinecone vector ID
    relevance_score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    access_count = Column(Integer, default=0)
