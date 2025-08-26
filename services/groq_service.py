"""GROQ service for LLM integration in EUNA MVP."""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from groq import Groq
import json

from config.settings import settings

logger = logging.getLogger(__name__)


class GroqService:
    """Service for interacting with GROQ LLM API."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.default_model = "mixtral-8x7b-32768"
        self.max_retries = 3
    
    async def analyze_task(self, user_input: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze user task and determine agent requirements."""
        
        system_prompt = """You are EUNA's task analyzer. Analyze the user's request and determine:
1. Task complexity (simple, moderate, complex)
2. Required agent types (default agents or need for dynamic agents)
3. Suggested agent roles and capabilities
4. Tools that might be needed
5. Expected workflow steps

Default agents available:
- SummarizerAgent: Text summarization and key point extraction
- SearchAgent: Web search and information gathering  
- CodingAgent: Code generation, review, and debugging
- SchedulerAgent: Task scheduling and time management

Respond in JSON format with this structure:
{
    "complexity": "simple|moderate|complex",
    "requires_dynamic_agents": boolean,
    "suggested_agents": [
        {
            "name": "agent_name",
            "type": "default|dynamic", 
            "role": "specific role description",
            "capabilities": ["capability1", "capability2"],
            "priority": "high|medium|low"
        }
    ],
    "required_tools": ["tool1", "tool2"],
    "workflow_steps": ["step1", "step2"],
    "estimated_duration": "time estimate"
}"""
        
        user_prompt = f"Task: {user_input}"
        if context:
            user_prompt += f"\nContext: {json.dumps(context, indent=2)}"
        
        try:
            response = await self._make_completion_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1
            )
            
            # Parse JSON response
            analysis = json.loads(response)
            logger.info(f"Task analysis completed: {analysis.get('complexity')} complexity")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing task: {e}")
            # Return fallback analysis
            return {
                "complexity": "moderate",
                "requires_dynamic_agents": False,
                "suggested_agents": [
                    {
                        "name": "GeneralAgent",
                        "type": "default",
                        "role": "Handle general task processing",
                        "capabilities": ["reasoning", "analysis"],
                        "priority": "high"
                    }
                ],
                "required_tools": ["web_search"],
                "workflow_steps": ["analyze", "process", "respond"],
                "estimated_duration": "2-5 minutes"
            }
    
    async def generate_dynamic_agent(self, agent_spec: Dict[str, Any], task_context: str) -> Dict[str, Any]:
        """Generate a dynamic agent based on specifications."""
        
        system_prompt = """You are EUNA's dynamic agent generator. Create a specialized agent based on the provided specifications.

Generate a complete agent definition with:
1. Detailed role description
2. Specific capabilities and skills
3. System prompt template for the agent
4. Preferred tools and methods
5. Success criteria and validation steps

Respond in JSON format:
{
    "name": "agent_name",
    "role": "detailed role description",
    "capabilities": ["specific_capability1", "specific_capability2"],
    "system_prompt": "detailed system prompt for the agent",
    "preferred_tools": ["tool1", "tool2"],
    "success_criteria": ["criteria1", "criteria2"],
    "validation_steps": ["step1", "step2"],
    "specialization": "area of expertise"
}"""
        
        user_prompt = f"""Create an agent with these specifications:
Name: {agent_spec.get('name')}
Role: {agent_spec.get('role')}
Required Capabilities: {agent_spec.get('capabilities', [])}
Priority: {agent_spec.get('priority', 'medium')}

Task Context: {task_context}

Make this agent highly specialized for the specific task requirements."""
        
        try:
            response = await self._make_completion_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            )
            
            agent_definition = json.loads(response)
            logger.info(f"Generated dynamic agent: {agent_definition.get('name')}")
            return agent_definition
            
        except Exception as e:
            logger.error(f"Error generating dynamic agent: {e}")
            # Return fallback agent
            return {
                "name": agent_spec.get('name', 'DynamicAgent'),
                "role": agent_spec.get('role', 'General purpose agent'),
                "capabilities": agent_spec.get('capabilities', ['reasoning']),
                "system_prompt": f"You are a {agent_spec.get('name', 'specialized')} agent. {agent_spec.get('role', 'Handle the assigned task effectively.')}",
                "preferred_tools": ["web_search", "calculator"],
                "success_criteria": ["Complete the assigned task"],
                "validation_steps": ["Verify output quality"],
                "specialization": "General"
            }
    
    async def execute_agent_reasoning(self, agent_prompt: str, task_input: str, 
                                    context: Optional[Dict] = None, tools_available: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute agent reasoning and decision making."""
        
        system_prompt = f"""{agent_prompt}

Available tools: {', '.join(tools_available) if tools_available else 'None'}

Your response should include:
1. Your reasoning process
2. Actions you want to take
3. Tools you need to use
4. Expected outcomes

Respond in JSON format:
{{
    "reasoning": "your thought process",
    "planned_actions": ["action1", "action2"],
    "tools_needed": ["tool1", "tool2"],
    "expected_outcome": "what you expect to achieve",
    "confidence_level": "high|medium|low",
    "next_steps": ["step1", "step2"]
}}"""
        
        user_prompt = f"Task Input: {task_input}"
        if context:
            user_prompt += f"\nContext: {json.dumps(context, indent=2)}"
        
        try:
            response = await self._make_completion_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2
            )
            
            reasoning_result = json.loads(response)
            logger.info(f"Agent reasoning completed with {reasoning_result.get('confidence_level')} confidence")
            return reasoning_result
            
        except Exception as e:
            logger.error(f"Error in agent reasoning: {e}")
            return {
                "reasoning": "Unable to process request due to error",
                "planned_actions": ["report_error"],
                "tools_needed": [],
                "expected_outcome": "Error handling",
                "confidence_level": "low",
                "next_steps": ["retry_or_escalate"]
            }
    
    async def synthesize_results(self, agent_results: List[Dict], original_task: str) -> Dict[str, Any]:
        """Synthesize results from multiple agents into final response."""
        
        system_prompt = """You are EUNA's result synthesizer. Combine results from multiple agents into a comprehensive, coherent response.

Create a final response that:
1. Addresses the original user request completely
2. Integrates insights from all agents
3. Provides clear, actionable information
4. Highlights key findings and recommendations

Respond in JSON format:
{
    "final_answer": "comprehensive response to user",
    "key_insights": ["insight1", "insight2"],
    "recommendations": ["recommendation1", "recommendation2"],
    "supporting_evidence": ["evidence1", "evidence2"],
    "confidence_score": 0.0-1.0,
    "follow_up_suggestions": ["suggestion1", "suggestion2"]
}"""
        
        user_prompt = f"""Original Task: {original_task}

Agent Results:
{json.dumps(agent_results, indent=2)}

Synthesize these results into a comprehensive response."""
        
        try:
            response = await self._make_completion_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1
            )
            
            synthesis = json.loads(response)
            logger.info(f"Result synthesis completed with confidence: {synthesis.get('confidence_score', 0)}")
            return synthesis
            
        except Exception as e:
            logger.error(f"Error synthesizing results: {e}")
            return {
                "final_answer": "Multiple agents processed your request. Please check individual agent results for details.",
                "key_insights": ["Processing completed by multiple agents"],
                "recommendations": ["Review individual agent outputs"],
                "supporting_evidence": [],
                "confidence_score": 0.5,
                "follow_up_suggestions": ["Ask for clarification if needed"]
            }
    
    async def _make_completion_request(self, system_prompt: str, user_prompt: str, 
                                     temperature: float = 0.1, max_tokens: int = 2000) -> str:
        """Make a completion request to GROQ API with retry logic."""
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.default_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.warning(f"GROQ API attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        raise Exception("All GROQ API attempts failed")


# Global GROQ service instance
groq_service = GroqService()
