"""Default agent implementations for EUNA MVP."""

import logging
from typing import Dict, List, Any, Optional

from agents.base_agent import BaseAgent, AgentExecutionContext
from tools.tool_executor import tool_executor

logger = logging.getLogger(__name__)


class SummarizerAgent(BaseAgent):
    """Agent specialized in text summarization and key point extraction."""
    
    def __init__(self, agent_id: int):
        super().__init__(
            agent_id=agent_id,
            name="SummarizerAgent",
            role="Text summarization and key point extraction specialist",
            capabilities=["text_analysis", "summarization", "key_extraction", "content_organization"]
        )
    
    async def execute(self, task_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute summarization task."""
        
        self.status = "active"
        execution_context = AgentExecutionContext(
            task_id=context.get("task_id", 0),
            user_input=task_input,
            session_context=context
        )
        
        try:
            # Plan actions
            actions = await self.plan_actions(task_input, context)
            
            # Execute text summarization
            summary_result = await tool_executor.execute_single_tool(
                agent_id=self.agent_id,
                tool_name="text_summarizer",
                parameters={"text": task_input, "max_sentences": 3}
            )
            
            execution_context.add_tool_result("text_summarizer", summary_result)
            
            # Extract key points (simple implementation)
            key_points = self._extract_key_points(task_input)
            
            # Compile result
            result = {
                "success": summary_result.get("success", False),
                "agent_name": self.name,
                "summary": summary_result.get("result", {}).get("summary", ""),
                "key_points": key_points,
                "original_length": len(task_input),
                "summary_length": len(summary_result.get("result", {}).get("summary", "")),
                "compression_ratio": summary_result.get("result", {}).get("compression_ratio", 0),
                "tools_used": ["text_summarizer"],
                "confidence_level": "high" if summary_result.get("success") else "low",
                "execution_time": execution_context.get_execution_duration()
            }
            
            self.status = "completed"
            self.log_execution(task_input, result)
            
            return result
            
        except Exception as e:
            logger.error(f"SummarizerAgent execution error: {e}")
            self.status = "failed"
            
            result = {
                "success": False,
                "agent_name": self.name,
                "error": str(e),
                "tools_used": [],
                "confidence_level": "low"
            }
            
            self.log_execution(task_input, result)
            return result
    
    async def plan_actions(self, task_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan summarization actions."""
        
        actions = [
            {
                "action": "analyze_text",
                "description": "Analyze text structure and content",
                "tool": "text_summarizer",
                "priority": "high"
            },
            {
                "action": "extract_key_points",
                "description": "Extract main themes and important points",
                "tool": "internal_processing",
                "priority": "medium"
            },
            {
                "action": "create_summary",
                "description": "Generate concise summary",
                "tool": "text_summarizer",
                "priority": "high"
            }
        ]
        
        return actions
    
    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from text (simplified implementation)."""
        
        # Simple key point extraction based on sentence patterns
        import re
        
        sentences = re.split(r'[.!?]+', text)
        key_points = []
        
        # Look for sentences with key indicators
        key_indicators = [
            "important", "key", "main", "primary", "essential", "critical",
            "significant", "major", "crucial", "vital", "fundamental"
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Minimum length
                if any(indicator in sentence.lower() for indicator in key_indicators):
                    key_points.append(sentence)
                elif sentence.startswith(("First", "Second", "Third", "Finally", "In conclusion")):
                    key_points.append(sentence)
        
        # If no key points found, take first few sentences
        if not key_points:
            key_points = [s.strip() for s in sentences[:3] if s.strip() and len(s.strip()) > 20]
        
        return key_points[:5]  # Limit to 5 key points


class SearchAgent(BaseAgent):
    """Agent specialized in web search and information gathering."""
    
    def __init__(self, agent_id: int):
        super().__init__(
            agent_id=agent_id,
            name="SearchAgent",
            role="Web search and information gathering specialist",
            capabilities=["web_search", "information_gathering", "fact_checking", "research"]
        )
    
    async def execute(self, task_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search task."""
        
        self.status = "active"
        execution_context = AgentExecutionContext(
            task_id=context.get("task_id", 0),
            user_input=task_input,
            session_context=context
        )
        
        try:
            # Extract search query from task input
            search_query = self._extract_search_query(task_input)
            
            # Execute web search
            search_result = await tool_executor.execute_single_tool(
                agent_id=self.agent_id,
                tool_name="web_search",
                parameters={"query": search_query, "max_results": 5}
            )
            
            execution_context.add_tool_result("web_search", search_result)
            
            # Process search results
            processed_results = self._process_search_results(
                search_result.get("result", {}).get("results", [])
            )
            
            # Compile result
            result = {
                "success": search_result.get("success", False),
                "agent_name": self.name,
                "search_query": search_query,
                "total_results": search_result.get("result", {}).get("total_results", 0),
                "processed_results": processed_results,
                "summary": self._create_search_summary(processed_results),
                "sources": [r.get("url", "") for r in processed_results],
                "tools_used": ["web_search"],
                "confidence_level": "high" if search_result.get("success") and processed_results else "medium",
                "execution_time": execution_context.get_execution_duration()
            }
            
            self.status = "completed"
            self.log_execution(task_input, result)
            
            return result
            
        except Exception as e:
            logger.error(f"SearchAgent execution error: {e}")
            self.status = "failed"
            
            result = {
                "success": False,
                "agent_name": self.name,
                "error": str(e),
                "tools_used": [],
                "confidence_level": "low"
            }
            
            self.log_execution(task_input, result)
            return result
    
    async def plan_actions(self, task_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan search actions."""
        
        actions = [
            {
                "action": "extract_search_terms",
                "description": "Extract relevant search terms from input",
                "tool": "internal_processing",
                "priority": "high"
            },
            {
                "action": "web_search",
                "description": "Search the web for relevant information",
                "tool": "web_search",
                "priority": "high"
            },
            {
                "action": "process_results",
                "description": "Process and organize search results",
                "tool": "internal_processing",
                "priority": "medium"
            }
        ]
        
        return actions
    
    def _extract_search_query(self, task_input: str) -> str:
        """Extract search query from task input."""
        
        # Remove common task prefixes
        query = task_input.lower()
        prefixes_to_remove = [
            "search for", "find", "look up", "research", "tell me about",
            "what is", "who is", "where is", "when is", "how to"
        ]
        
        for prefix in prefixes_to_remove:
            if query.startswith(prefix):
                query = query[len(prefix):].strip()
                break
        
        # Clean up query
        query = query.replace("?", "").replace("!", "").strip()
        
        return query if query else task_input
    
    def _process_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and enhance search results."""
        
        processed = []
        
        for result in results:
            processed_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "relevance_score": self._calculate_relevance_score(result),
                "source_type": self._determine_source_type(result.get("url", ""))
            }
            processed.append(processed_result)
        
        # Sort by relevance score
        processed.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return processed
    
    def _calculate_relevance_score(self, result: Dict[str, Any]) -> float:
        """Calculate relevance score for search result."""
        
        score = 0.5  # Base score
        
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        
        # Boost score for authoritative sources
        url = result.get("url", "").lower()
        if any(domain in url for domain in ["wikipedia.org", "gov", "edu", "stackoverflow.com"]):
            score += 0.3
        
        # Boost score for recent content indicators
        if any(term in snippet for term in ["2024", "2023", "recent", "latest", "new"]):
            score += 0.1
        
        # Boost score for comprehensive content indicators
        if any(term in title for term in ["guide", "tutorial", "complete", "comprehensive"]):
            score += 0.1
        
        return min(score, 1.0)
    
    def _determine_source_type(self, url: str) -> str:
        """Determine the type of source based on URL."""
        
        url_lower = url.lower()
        
        if "wikipedia.org" in url_lower:
            return "encyclopedia"
        elif any(domain in url_lower for domain in [".gov", ".edu"]):
            return "official"
        elif "stackoverflow.com" in url_lower:
            return "technical"
        elif any(domain in url_lower for domain in ["news", "reuters", "bbc", "cnn"]):
            return "news"
        elif "blog" in url_lower:
            return "blog"
        else:
            return "general"
    
    def _create_search_summary(self, results: List[Dict[str, Any]]) -> str:
        """Create summary of search results."""
        
        if not results:
            return "No relevant information found."
        
        summary_parts = []
        
        # Add overview
        summary_parts.append(f"Found {len(results)} relevant sources:")
        
        # Add top results
        for i, result in enumerate(results[:3], 1):
            title = result["title"][:80] + "..." if len(result["title"]) > 80 else result["title"]
            source_type = result["source_type"]
            summary_parts.append(f"{i}. {title} ({source_type} source)")
        
        return "\n".join(summary_parts)


class CodingAgent(BaseAgent):
    """Agent specialized in code generation, review, and debugging."""
    
    def __init__(self, agent_id: int):
        super().__init__(
            agent_id=agent_id,
            name="CodingAgent",
            role="Code generation, review, and debugging specialist",
            capabilities=["code_generation", "code_review", "debugging", "syntax_checking", "documentation"]
        )
    
    async def execute(self, task_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coding task."""
        
        self.status = "active"
        execution_context = AgentExecutionContext(
            task_id=context.get("task_id", 0),
            user_input=task_input,
            session_context=context
        )
        
        try:
            # Determine coding task type
            task_type = self._determine_task_type(task_input)
            
            # Execute based on task type
            if task_type == "generation":
                result = await self._handle_code_generation(task_input, execution_context)
            elif task_type == "review":
                result = await self._handle_code_review(task_input, execution_context)
            elif task_type == "debugging":
                result = await self._handle_debugging(task_input, execution_context)
            else:
                result = await self._handle_general_coding(task_input, execution_context)
            
            self.status = "completed"
            self.log_execution(task_input, result)
            
            return result
            
        except Exception as e:
            logger.error(f"CodingAgent execution error: {e}")
            self.status = "failed"
            
            result = {
                "success": False,
                "agent_name": self.name,
                "error": str(e),
                "tools_used": [],
                "confidence_level": "low"
            }
            
            self.log_execution(task_input, result)
            return result
    
    async def plan_actions(self, task_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan coding actions."""
        
        task_type = self._determine_task_type(task_input)
        
        if task_type == "generation":
            actions = [
                {"action": "analyze_requirements", "tool": "internal_processing", "priority": "high"},
                {"action": "design_solution", "tool": "internal_processing", "priority": "high"},
                {"action": "generate_code", "tool": "internal_processing", "priority": "high"},
                {"action": "validate_syntax", "tool": "internal_processing", "priority": "medium"}
            ]
        elif task_type == "review":
            actions = [
                {"action": "read_code", "tool": "file_reader", "priority": "high"},
                {"action": "analyze_code", "tool": "internal_processing", "priority": "high"},
                {"action": "check_best_practices", "tool": "internal_processing", "priority": "medium"}
            ]
        else:
            actions = [
                {"action": "understand_problem", "tool": "internal_processing", "priority": "high"},
                {"action": "research_solution", "tool": "web_search", "priority": "medium"},
                {"action": "provide_solution", "tool": "internal_processing", "priority": "high"}
            ]
        
        return actions
    
    def _determine_task_type(self, task_input: str) -> str:
        """Determine the type of coding task."""
        
        task_lower = task_input.lower()
        
        if any(term in task_lower for term in ["generate", "create", "write", "build", "implement"]):
            return "generation"
        elif any(term in task_lower for term in ["review", "check", "analyze", "audit"]):
            return "review"
        elif any(term in task_lower for term in ["debug", "fix", "error", "bug", "issue"]):
            return "debugging"
        else:
            return "general"
    
    async def _handle_code_generation(self, task_input: str, context: AgentExecutionContext) -> Dict[str, Any]:
        """Handle code generation tasks."""
        
        # Extract programming language and requirements
        language = self._extract_programming_language(task_input)
        requirements = self._extract_requirements(task_input)
        
        # Generate code (simplified implementation)
        generated_code = self._generate_code_template(language, requirements)
        
        return {
            "success": True,
            "agent_name": self.name,
            "task_type": "code_generation",
            "language": language,
            "requirements": requirements,
            "generated_code": generated_code,
            "explanation": self._explain_code(generated_code),
            "tools_used": ["internal_processing"],
            "confidence_level": "medium",
            "execution_time": context.get_execution_duration()
        }
    
    async def _handle_code_review(self, task_input: str, context: AgentExecutionContext) -> Dict[str, Any]:
        """Handle code review tasks."""
        
        # Extract code from input (simplified)
        code_snippet = self._extract_code_snippet(task_input)
        
        # Perform review
        review_results = self._review_code(code_snippet)
        
        return {
            "success": True,
            "agent_name": self.name,
            "task_type": "code_review",
            "code_snippet": code_snippet,
            "review_results": review_results,
            "tools_used": ["internal_processing"],
            "confidence_level": "high",
            "execution_time": context.get_execution_duration()
        }
    
    async def _handle_debugging(self, task_input: str, context: AgentExecutionContext) -> Dict[str, Any]:
        """Handle debugging tasks."""
        
        # Extract error information
        error_info = self._extract_error_info(task_input)
        
        # Provide debugging suggestions
        suggestions = self._generate_debug_suggestions(error_info)
        
        return {
            "success": True,
            "agent_name": self.name,
            "task_type": "debugging",
            "error_info": error_info,
            "debug_suggestions": suggestions,
            "tools_used": ["internal_processing"],
            "confidence_level": "medium",
            "execution_time": context.get_execution_duration()
        }
    
    async def _handle_general_coding(self, task_input: str, context: AgentExecutionContext) -> Dict[str, Any]:
        """Handle general coding questions."""
        
        # Search for relevant information if needed
        search_result = await tool_executor.execute_single_tool(
            agent_id=self.agent_id,
            tool_name="web_search",
            parameters={"query": f"programming {task_input}", "max_results": 3}
        )
        
        context.add_tool_result("web_search", search_result)
        
        return {
            "success": search_result.get("success", False),
            "agent_name": self.name,
            "task_type": "general_coding",
            "search_results": search_result.get("result", {}),
            "guidance": "Based on search results, here are some relevant resources and information.",
            "tools_used": ["web_search"],
            "confidence_level": "medium",
            "execution_time": context.get_execution_duration()
        }
    
    def _extract_programming_language(self, task_input: str) -> str:
        """Extract programming language from task input."""
        
        languages = ["python", "javascript", "java", "c++", "c#", "go", "rust", "php", "ruby"]
        task_lower = task_input.lower()
        
        for lang in languages:
            if lang in task_lower:
                return lang
        
        return "python"  # Default
    
    def _extract_requirements(self, task_input: str) -> List[str]:
        """Extract requirements from task input."""
        
        # Simple requirement extraction
        requirements = []
        
        if "function" in task_input.lower():
            requirements.append("Create a function")
        if "class" in task_input.lower():
            requirements.append("Create a class")
        if "api" in task_input.lower():
            requirements.append("API integration")
        if "database" in task_input.lower():
            requirements.append("Database operations")
        
        return requirements if requirements else ["General implementation"]
    
    def _generate_code_template(self, language: str, requirements: List[str]) -> str:
        """Generate basic code template."""
        
        if language == "python":
            return '''def example_function():
    """
    Example function implementation.
    Modify according to your specific requirements.
    """
    # TODO: Implement your logic here
    pass

# Example usage
if __name__ == "__main__":
    result = example_function()
    print(result)'''
        
        elif language == "javascript":
            return '''function exampleFunction() {
    /**
     * Example function implementation.
     * Modify according to your specific requirements.
     */
    // TODO: Implement your logic here
    return null;
}

// Example usage
const result = exampleFunction();
console.log(result);'''
        
        else:
            return f"// {language} code template\n// TODO: Implement your solution here"
    
    def _explain_code(self, code: str) -> str:
        """Provide explanation for generated code."""
        
        return """This is a basic template that includes:
1. Function definition with documentation
2. TODO comment for implementation
3. Example usage
4. Proper structure and formatting

Modify the function name, parameters, and implementation according to your specific needs."""
    
    def _extract_code_snippet(self, task_input: str) -> str:
        """Extract code snippet from input."""
        
        # Look for code blocks
        import re
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', task_input, re.DOTALL)
        if code_blocks:
            return code_blocks[0]
        
        # Look for inline code
        inline_code = re.findall(r'`([^`]+)`', task_input)
        if inline_code:
            return inline_code[0]
        
        return task_input  # Return original if no code found
    
    def _review_code(self, code: str) -> Dict[str, Any]:
        """Perform basic code review."""
        
        issues = []
        suggestions = []
        
        # Basic checks
        if "TODO" in code:
            issues.append("Contains TODO comments - implementation incomplete")
        
        if len(code.split('\n')) > 50:
            suggestions.append("Consider breaking large functions into smaller ones")
        
        if not any(char in code for char in ['"', "'"]):
            suggestions.append("Add documentation strings for better maintainability")
        
        return {
            "issues": issues,
            "suggestions": suggestions,
            "overall_quality": "good" if len(issues) == 0 else "needs_improvement"
        }
    
    def _extract_error_info(self, task_input: str) -> Dict[str, Any]:
        """Extract error information from input."""
        
        return {
            "error_description": task_input,
            "potential_causes": ["Syntax error", "Logic error", "Runtime error"],
            "error_type": "general"
        }
    
    def _generate_debug_suggestions(self, error_info: Dict[str, Any]) -> List[str]:
        """Generate debugging suggestions."""
        
        return [
            "Check syntax and indentation",
            "Verify variable names and scope",
            "Add print statements for debugging",
            "Use a debugger to step through code",
            "Check for common error patterns"
        ]


class SchedulerAgent(BaseAgent):
    """Agent specialized in task scheduling and time management."""
    
    def __init__(self, agent_id: int):
        super().__init__(
            agent_id=agent_id,
            name="SchedulerAgent",
            role="Task scheduling and time management specialist",
            capabilities=["scheduling", "time_management", "calendar_operations", "deadline_tracking"]
        )
    
    async def execute(self, task_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scheduling task."""
        
        self.status = "active"
        execution_context = AgentExecutionContext(
            task_id=context.get("task_id", 0),
            user_input=task_input,
            session_context=context
        )
        
        try:
            # Get current date/time
            datetime_result = await tool_executor.execute_single_tool(
                agent_id=self.agent_id,
                tool_name="datetime_tool",
                parameters={"operation": "now"}
            )
            
            execution_context.add_tool_result("datetime_tool", datetime_result)
            
            # Parse scheduling request
            schedule_info = self._parse_schedule_request(task_input)
            
            # Create schedule
            schedule = self._create_schedule(schedule_info, datetime_result.get("result", {}))
            
            # Compile result
            result = {
                "success": True,
                "agent_name": self.name,
                "schedule_info": schedule_info,
                "created_schedule": schedule,
                "current_time": datetime_result.get("result", {}).get("current_datetime", ""),
                "tools_used": ["datetime_tool"],
                "confidence_level": "high",
                "execution_time": execution_context.get_execution_duration()
            }
            
            self.status = "completed"
            self.log_execution(task_input, result)
            
            return result
            
        except Exception as e:
            logger.error(f"SchedulerAgent execution error: {e}")
            self.status = "failed"
            
            result = {
                "success": False,
                "agent_name": self.name,
                "error": str(e),
                "tools_used": [],
                "confidence_level": "low"
            }
            
            self.log_execution(task_input, result)
            return result
    
    async def plan_actions(self, task_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan scheduling actions."""
        
        actions = [
            {
                "action": "get_current_time",
                "description": "Get current date and time",
                "tool": "datetime_tool",
                "priority": "high"
            },
            {
                "action": "parse_schedule_request",
                "description": "Parse scheduling requirements",
                "tool": "internal_processing",
                "priority": "high"
            },
            {
                "action": "create_schedule",
                "description": "Create optimized schedule",
                "tool": "internal_processing",
                "priority": "medium"
            }
        ]
        
        return actions
    
    def _parse_schedule_request(self, task_input: str) -> Dict[str, Any]:
        """Parse scheduling request from input."""
        
        import re
        
        # Extract time-related information
        time_patterns = {
            "duration": r'(\d+)\s*(hour|minute|day|week)s?',
            "deadline": r'(by|before|until)\s+(\w+)',
            "start_time": r'(at|from)\s+(\d{1,2}:\d{2}|\d{1,2}\s*(am|pm))',
            "date": r'(\d{1,2}/\d{1,2}|\w+day|\w+\s+\d{1,2})'
        }
        
        parsed_info = {
            "task_description": task_input,
            "duration": None,
            "deadline": None,
            "start_time": None,
            "date": None,
            "priority": "medium"
        }
        
        task_lower = task_input.lower()
        
        # Extract duration
        duration_match = re.search(time_patterns["duration"], task_lower)
        if duration_match:
            parsed_info["duration"] = f"{duration_match.group(1)} {duration_match.group(2)}s"
        
        # Extract deadline
        deadline_match = re.search(time_patterns["deadline"], task_lower)
        if deadline_match:
            parsed_info["deadline"] = deadline_match.group(2)
        
        # Determine priority
        if any(word in task_lower for word in ["urgent", "asap", "immediately"]):
            parsed_info["priority"] = "high"
        elif any(word in task_lower for word in ["later", "eventually", "when possible"]):
            parsed_info["priority"] = "low"
        
        return parsed_info
    
    def _create_schedule(self, schedule_info: Dict[str, Any], current_time_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create schedule based on parsed information."""
        
        from datetime import datetime, timedelta
        
        current_time = current_time_info.get("current_datetime", "")
        
        schedule = {
            "task": schedule_info["task_description"],
            "priority": schedule_info["priority"],
            "estimated_duration": schedule_info.get("duration", "1 hour"),
            "suggested_start_time": current_time,
            "deadline": schedule_info.get("deadline", "flexible"),
            "recommendations": []
        }
        
        # Add recommendations based on priority
        if schedule_info["priority"] == "high":
            schedule["recommendations"].append("Schedule immediately or within next 2 hours")
            schedule["recommendations"].append("Block calendar to avoid interruptions")
        elif schedule_info["priority"] == "medium":
            schedule["recommendations"].append("Schedule within next 24 hours")
            schedule["recommendations"].append("Consider batching with similar tasks")
        else:
            schedule["recommendations"].append("Schedule when convenient")
            schedule["recommendations"].append("Can be postponed if higher priority tasks arise")
        
        # Add time management tips
        schedule["time_management_tips"] = [
            "Break large tasks into smaller chunks",
            "Use time-blocking technique",
            "Set reminders 15 minutes before start time",
            "Prepare all necessary resources in advance"
        ]
        
        return schedule
