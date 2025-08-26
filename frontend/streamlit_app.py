"""Streamlit frontend for EUNA MVP."""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configure page
st.set_page_config(
    page_title="EUNA MVP - AI Agent Orchestration",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}

.agent-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
    border-left: 4px solid #1f77b4;
}

.success-message {
    background-color: #d4edda;
    color: #155724;
    padding: 0.75rem;
    border-radius: 0.25rem;
    border: 1px solid #c3e6cb;
}

.error-message {
    background-color: #f8d7da;
    color: #721c24;
    padding: 0.75rem;
    border-radius: 0.25rem;
    border: 1px solid #f5c6cb;
}

.info-message {
    background-color: #d1ecf1;
    color: #0c5460;
    padding: 0.75rem;
    border-radius: 0.25rem;
    border: 1px solid #bee5eb;
}
</style>
""", unsafe_allow_html=True)

# Utility functions
def make_api_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
    """Make API request to backend."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return {"error": str(e)}

def format_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str

def get_status_color(status: str) -> str:
    """Get color for status display."""
    colors = {
        "pending": "🟡",
        "in_progress": "🔵",
        "completed": "🟢",
        "failed": "🔴",
        "cancelled": "⚫"
    }
    return colors.get(status, "⚪")

# Initialize session state
if 'submitted_tasks' not in st.session_state:
    st.session_state.submitted_tasks = []
if 'selected_task_id' not in st.session_state:
    st.session_state.selected_task_id = None

# Main header
st.markdown('<div class="main-header">🤖 EUNA MVP - AI Agent Orchestration</div>', unsafe_allow_html=True)
st.markdown("**Evolvable Unified Neural Agent** - Dynamic AI agent creation and task orchestration")

# Sidebar
with st.sidebar:
    st.header("🎛️ Control Panel")
    
    # System health check
    with st.expander("System Health", expanded=False):
        if st.button("Check Health"):
            health = make_api_request("/health")
            if "error" not in health:
                st.success(f"Status: {health['status']}")
                st.info(f"Active Tasks: {health['active_tasks']}")
                st.info(f"Registered Tools: {health['registered_tools']}")
            else:
                st.error(f"Health check failed: {health['error']}")
    
    # Quick stats
    with st.expander("System Stats", expanded=False):
        if st.button("Get Stats"):
            stats = make_api_request("/api/v1/stats")
            if "error" not in stats:
                st.metric("Success Rate", f"{stats['tasks']['success_rate']:.1%}")
                st.metric("Active Tasks", stats['tasks']['active'])
                st.metric("Registered Tools", stats['tools']['registered'])
                st.metric("Active Agents", stats['agents']['active'])

# Main content tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Submit Task", 
    "📊 Task Monitor", 
    "🤖 Agents", 
    "🔧 Tools", 
    "📈 Analytics"
])

# Tab 1: Submit Task
with tab1:
    st.header("Submit New Task")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Task input form
        with st.form("task_submission"):
            user_input = st.text_area(
                "Describe your task:",
                placeholder="e.g., 'Plan a 3-day trip to Tokyo with a budget of $2000' or 'Summarize the latest AI research trends'",
                height=100
            )
            
            col_priority, col_session = st.columns(2)
            with col_priority:
                priority = st.selectbox("Priority", ["low", "medium", "high", "urgent"])
            with col_session:
                session_id = st.text_input("Session ID (optional)", placeholder="user_session_123")
            
            submitted = st.form_submit_button("🚀 Submit Task", use_container_width=True)
            
            if submitted and user_input:
                with st.spinner("Submitting task..."):
                    result = make_api_request(
                        "/api/v1/tasks/submit",
                        method="POST",
                        data={
                            "user_input": user_input,
                            "priority": priority,
                            "session_id": session_id if session_id else None
                        }
                    )
                    
                    if "error" not in result:
                        st.success(f"Task submitted successfully! Task ID: {result['task_id']}")
                        st.session_state.submitted_tasks.append(result['task_id'])
                        st.session_state.selected_task_id = result['task_id']
                        
                        # Show analysis
                        if result.get('analysis'):
                            st.json(result['analysis'])
                    else:
                        st.error(f"Failed to submit task: {result['error']}")
    
    with col2:
        st.subheader("Demo Examples")
        
        demo_tasks = [
            "Plan a weekend trip to San Francisco with restaurant recommendations",
            "Summarize the key points from a 10-page research paper on renewable energy",
            "Create a Python Flask API for user authentication with JWT tokens",
            "Research the latest trends in artificial intelligence and create a presentation outline",
            "Calculate the compound interest on $10,000 invested at 7% annually for 10 years"
        ]
        
        for i, task in enumerate(demo_tasks):
            if st.button(f"Use Example {i+1}", key=f"demo_{i}"):
                st.session_state.demo_task = task
                st.rerun()
        
        # Auto-fill demo task
        if 'demo_task' in st.session_state:
            st.code(st.session_state.demo_task)

# Tab 2: Task Monitor
with tab2:
    st.header("Task Monitoring")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Recent Tasks")
        
        # Get recent tasks
        recent_tasks = make_api_request("/api/v1/tasks?limit=20")
        
        if "error" not in recent_tasks and recent_tasks.get("tasks"):
            for task in recent_tasks["tasks"]:
                status_icon = get_status_color(task["status"])
                
                if st.button(
                    f"{status_icon} Task {task['task_id']}: {task['user_input'][:50]}...",
                    key=f"task_{task['task_id']}"
                ):
                    st.session_state.selected_task_id = task['task_id']
        else:
            st.info("No recent tasks found")
    
    with col2:
        st.subheader("Task Details")
        
        if st.session_state.selected_task_id:
            task_id = st.session_state.selected_task_id
            
            # Auto-refresh toggle
            auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
            
            if auto_refresh:
                time.sleep(0.1)  # Small delay to prevent too frequent updates
            
            # Get task status
            task_status = make_api_request(f"/api/v1/tasks/{task_id}")
            
            if "error" not in task_status:
                # Task overview
                status_icon = get_status_color(task_status["status"])
                st.markdown(f"**Status:** {status_icon} {task_status['status'].upper()}")
                st.markdown(f"**Task:** {task_status['user_input']}")
                
                # Progress bar
                if task_status.get("progress"):
                    progress = task_status["progress"]
                    total_agents = progress.get("total_agents", 1)
                    completed_agents = progress.get("completed_agents", 0)
                    progress_pct = completed_agents / total_agents if total_agents > 0 else 0
                    
                    st.progress(progress_pct)
                    st.caption(f"Progress: {completed_agents}/{total_agents} agents completed")
                
                # Agents
                if task_status.get("agents"):
                    st.subheader("Agents")
                    for agent in task_status["agents"]:
                        agent_status_icon = get_status_color(agent["status"])
                        st.markdown(f"- {agent_status_icon} **{agent['name']}** ({agent['type']}) - {agent['role']}")
                
                # Final result
                if task_status.get("final_result"):
                    st.subheader("Final Result")
                    result = task_status["final_result"]
                    
                    if result.get("final_answer"):
                        st.markdown("**Answer:**")
                        st.markdown(result["final_answer"])
                    
                    if result.get("key_insights"):
                        st.markdown("**Key Insights:**")
                        for insight in result["key_insights"]:
                            st.markdown(f"- {insight}")
                    
                    if result.get("confidence_score"):
                        st.metric("Confidence Score", f"{result['confidence_score']:.2f}")
                
                # Logs
                if task_status.get("logs"):
                    with st.expander("Execution Logs"):
                        for log in task_status["logs"]:
                            timestamp = format_timestamp(log["timestamp"])
                            level_colors = {
                                "INFO": "🔵",
                                "WARNING": "🟡", 
                                "ERROR": "🔴",
                                "DEBUG": "⚪"
                            }
                            level_icon = level_colors.get(log["level"], "⚪")
                            st.text(f"{timestamp} {level_icon} {log['message']}")
            
            else:
                st.error(f"Task not found: {task_status['error']}")
        else:
            st.info("Select a task from the list to view details")

# Tab 3: Agents
with tab3:
    st.header("Agent Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Active Agents")
        
        active_agents = make_api_request("/api/v1/agents/active")
        
        if "error" not in active_agents and active_agents.get("active_agents"):
            for agent in active_agents["active_agents"]:
                st.markdown(f"""
                <div class="agent-card">
                    <strong>{agent['name']}</strong> ({agent['type']})<br>
                    <em>{agent['role']}</em><br>
                    Task ID: {agent['task_id']}<br>
                    Created: {format_timestamp(agent['created_at'])}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No active agents")
    
    with col2:
        st.subheader("Available Agent Types")
        
        agent_types = make_api_request("/api/v1/agent-types")
        
        if "error" not in agent_types and agent_types.get("agent_types"):
            for agent_type, info in agent_types["agent_types"].items():
                with st.expander(f"🤖 {agent_type}"):
                    st.markdown(f"**Role:** {info['role']}")
                    st.markdown(f"**Capabilities:** {', '.join(info['capabilities'])}")
                    st.markdown(f"**Description:** {info['description']}")
        
        # Manual agent creation
        st.subheader("Create Custom Agent")
        with st.form("create_agent"):
            task_id_input = st.number_input("Task ID", min_value=1, value=1)
            agent_type_input = st.text_input("Agent Type", placeholder="CustomAgent")
            role_input = st.text_area("Role Description", placeholder="Describe the agent's role...")
            
            if st.form_submit_button("Create Agent"):
                result = make_api_request(
                    "/api/v1/agents/create",
                    method="POST",
                    data={
                        "task_id": task_id_input,
                        "agent_type": agent_type_input,
                        "role": role_input
                    }
                )
                
                if "error" not in result:
                    st.success("Agent created successfully!")
                    st.json(result["agent"])
                else:
                    st.error(f"Failed to create agent: {result['error']}")

# Tab 4: Tools
with tab4:
    st.header("Available Tools")
    
    tools_data = make_api_request("/api/v1/tools")
    
    if "error" not in tools_data and tools_data.get("categories"):
        st.metric("Total Tools", tools_data["total_tools"])
        
        for category, tools in tools_data["categories"].items():
            if tools:  # Only show categories with tools
                st.subheader(f"🔧 {category.title()}")
                
                for tool in tools:
                    with st.expander(f"{tool['name']}"):
                        st.markdown(f"**Description:** {tool['description']}")
                        
                        if tool.get("parameters"):
                            st.markdown("**Parameters:**")
                            params = tool["parameters"]
                            
                            if params.get("required"):
                                st.markdown(f"- Required: {', '.join(params['required'])}")
                            if params.get("optional"):
                                st.markdown(f"- Optional: {', '.join(params['optional'])}")
    else:
        st.error("Failed to load tools information")

# Tab 5: Analytics
with tab5:
    st.header("System Analytics")
    
    # Get system stats
    stats = make_api_request("/api/v1/stats")
    
    if "error" not in stats:
        # Task statistics
        st.subheader("📊 Task Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tasks", stats["tasks"]["total_recent"])
        with col2:
            st.metric("Completed", stats["tasks"]["completed"])
        with col3:
            st.metric("Failed", stats["tasks"]["failed"])
        with col4:
            st.metric("Success Rate", f"{stats['tasks']['success_rate']:.1%}")
        
        # Task status distribution
        if stats["tasks"]["total_recent"] > 0:
            task_data = {
                "Status": ["Completed", "Failed", "Active"],
                "Count": [
                    stats["tasks"]["completed"],
                    stats["tasks"]["failed"],
                    stats["tasks"]["active"]
                ]
            }
            
            fig = px.pie(
                values=task_data["Count"],
                names=task_data["Status"],
                title="Task Status Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Tool usage statistics
        st.subheader("🔧 Tool Usage")
        
        tool_stats = stats["tools"]["usage_stats"]
        if tool_stats.get("tool_usage_counts"):
            tool_df = pd.DataFrame([
                {"Tool": tool, "Usage Count": count}
                for tool, count in tool_stats["tool_usage_counts"].items()
            ])
            
            fig = px.bar(
                tool_df,
                x="Tool",
                y="Usage Count",
                title="Tool Usage Frequency"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Success rates by tool
        if tool_stats.get("success_rates"):
            success_df = pd.DataFrame([
                {"Tool": tool, "Success Rate": rate}
                for tool, rate in tool_stats["success_rates"].items()
            ])
            
            fig = px.bar(
                success_df,
                x="Tool",
                y="Success Rate",
                title="Tool Success Rates",
                color="Success Rate",
                color_continuous_scale="RdYlGn"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.error("Failed to load analytics data")

# Footer
st.markdown("---")
st.markdown(
    "🤖 **EUNA MVP** - Evolvable Unified Neural Agent | "
    "Built with Streamlit, FastAPI, and GROQ | "
    f"API Status: {'🟢 Connected' if make_api_request('/health').get('status') == 'healthy' else '🔴 Disconnected'}"
)

# Auto-refresh for active monitoring
if st.session_state.selected_task_id and 'auto_refresh' in locals() and auto_refresh:
    time.sleep(5)
    st.rerun()
