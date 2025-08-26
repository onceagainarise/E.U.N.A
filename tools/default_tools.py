"""Default tools for EUNA MVP."""

import logging
import asyncio
import json
import math
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

from tools.tool_registry import Tool

logger = logging.getLogger(__name__)


class WebSearchTool(Tool):
    """Web search tool using DuckDuckGo."""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for information using DuckDuckGo",
            parameters={
                "required": ["query"],
                "optional": ["max_results"],
                "query": "Search query string",
                "max_results": "Maximum number of results to return (default: 5)"
            }
        )
    
    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Execute web search."""
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = []
                for result in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", ""),
                        "source": "DuckDuckGo"
                    })
                
                return {
                    "query": query,
                    "results": results,
                    "total_results": len(results)
                }
                
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "error": str(e)
            }


class CalculatorTool(Tool):
    """Calculator tool for mathematical operations."""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations",
            parameters={
                "required": ["expression"],
                "expression": "Mathematical expression to evaluate"
            }
        )
    
    async def execute(self, expression: str) -> Dict[str, Any]:
        """Execute calculation."""
        try:
            # Sanitize expression for security
            allowed_chars = set("0123456789+-*/().% ")
            allowed_functions = ["sin", "cos", "tan", "log", "sqrt", "abs", "pow"]
            
            # Basic validation
            if not all(c in allowed_chars or any(func in expression for func in allowed_functions) for c in expression):
                raise ValueError("Invalid characters in expression")
            
            # Replace function names with math module equivalents
            safe_expression = expression
            for func in allowed_functions:
                safe_expression = safe_expression.replace(func, f"math.{func}")
            
            # Evaluate safely
            result = eval(safe_expression, {"__builtins__": {}, "math": math})
            
            return {
                "expression": expression,
                "result": result,
                "formatted_result": f"{result:,.6f}".rstrip('0').rstrip('.')
            }
            
        except Exception as e:
            logger.error(f"Calculator error: {e}")
            return {
                "expression": expression,
                "result": None,
                "error": str(e)
            }


class TextSummarizerTool(Tool):
    """Text summarization tool."""
    
    def __init__(self):
        super().__init__(
            name="text_summarizer",
            description="Summarize long text content",
            parameters={
                "required": ["text"],
                "optional": ["max_sentences"],
                "text": "Text content to summarize",
                "max_sentences": "Maximum sentences in summary (default: 3)"
            }
        )
    
    async def execute(self, text: str, max_sentences: int = 3) -> Dict[str, Any]:
        """Execute text summarization."""
        try:
            # Simple extractive summarization
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) <= max_sentences:
                summary = text
            else:
                # Score sentences by word frequency
                words = re.findall(r'\w+', text.lower())
                word_freq = {}
                for word in words:
                    word_freq[word] = word_freq.get(word, 0) + 1
                
                sentence_scores = []
                for sentence in sentences:
                    sentence_words = re.findall(r'\w+', sentence.lower())
                    score = sum(word_freq.get(word, 0) for word in sentence_words)
                    sentence_scores.append((score, sentence))
                
                # Get top sentences
                sentence_scores.sort(reverse=True)
                top_sentences = [sent for _, sent in sentence_scores[:max_sentences]]
                
                # Maintain original order
                summary_sentences = []
                for sentence in sentences:
                    if sentence in top_sentences:
                        summary_sentences.append(sentence)
                        if len(summary_sentences) >= max_sentences:
                            break
                
                summary = '. '.join(summary_sentences) + '.'
            
            return {
                "original_length": len(text),
                "summary_length": len(summary),
                "compression_ratio": len(summary) / len(text),
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Text summarizer error: {e}")
            return {
                "original_length": len(text),
                "summary": text[:500] + "..." if len(text) > 500 else text,
                "error": str(e)
            }


class FileReaderTool(Tool):
    """File reading tool."""
    
    def __init__(self):
        super().__init__(
            name="file_reader",
            description="Read content from files",
            parameters={
                "required": ["file_path"],
                "optional": ["encoding"],
                "file_path": "Path to the file to read",
                "encoding": "File encoding (default: utf-8)"
            }
        )
    
    async def execute(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Execute file reading."""
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read()
            
            return {
                "file_path": file_path,
                "content": content,
                "size": len(content),
                "lines": len(content.split('\n'))
            }
            
        except Exception as e:
            logger.error(f"File reader error: {e}")
            return {
                "file_path": file_path,
                "content": None,
                "error": str(e)
            }


class JSONParserTool(Tool):
    """JSON parsing and processing tool."""
    
    def __init__(self):
        super().__init__(
            name="json_parser",
            description="Parse and process JSON data",
            parameters={
                "required": ["json_data"],
                "optional": ["query_path"],
                "json_data": "JSON string or data to process",
                "query_path": "JSONPath query to extract specific data"
            }
        )
    
    async def execute(self, json_data: str, query_path: Optional[str] = None) -> Dict[str, Any]:
        """Execute JSON parsing."""
        try:
            # Parse JSON if string
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data
            
            result = {
                "parsed_data": data,
                "data_type": type(data).__name__,
                "size": len(json.dumps(data))
            }
            
            # Apply query path if provided (simplified implementation)
            if query_path:
                try:
                    # Simple dot notation query
                    keys = query_path.split('.')
                    queried_data = data
                    for key in keys:
                        if isinstance(queried_data, dict):
                            queried_data = queried_data.get(key)
                        elif isinstance(queried_data, list) and key.isdigit():
                            queried_data = queried_data[int(key)]
                        else:
                            queried_data = None
                            break
                    
                    result["queried_data"] = queried_data
                except Exception as e:
                    result["query_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"JSON parser error: {e}")
            return {
                "parsed_data": None,
                "error": str(e)
            }


class HTTPRequestTool(Tool):
    """HTTP request tool for API calls."""
    
    def __init__(self):
        super().__init__(
            name="http_request",
            description="Make HTTP requests to APIs",
            parameters={
                "required": ["url"],
                "optional": ["method", "headers", "data", "timeout"],
                "url": "URL to make request to",
                "method": "HTTP method (GET, POST, PUT, DELETE)",
                "headers": "Request headers as dictionary",
                "data": "Request body data",
                "timeout": "Request timeout in seconds"
            }
        )
    
    async def execute(self, url: str, method: str = "GET", 
                     headers: Optional[Dict] = None, data: Optional[Any] = None, 
                     timeout: int = 30) -> Dict[str, Any]:
        """Execute HTTP request."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    json=data if isinstance(data, dict) else None,
                    data=data if not isinstance(data, dict) else None
                )
                
                # Try to parse JSON response
                try:
                    response_data = response.json()
                except:
                    response_data = response.text
                
                return {
                    "url": url,
                    "method": method,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "data": response_data,
                    "success": 200 <= response.status_code < 300
                }
                
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            return {
                "url": url,
                "method": method,
                "error": str(e),
                "success": False
            }


class DateTimeTool(Tool):
    """Date and time utility tool."""
    
    def __init__(self):
        super().__init__(
            name="datetime_tool",
            description="Get current date/time and perform date calculations",
            parameters={
                "optional": ["operation", "date_string", "days_offset"],
                "operation": "Operation to perform (now, parse, add_days, format)",
                "date_string": "Date string to parse",
                "days_offset": "Number of days to add/subtract",
                "format": "Date format string"
            }
        )
    
    async def execute(self, operation: str = "now", **kwargs) -> Dict[str, Any]:
        """Execute date/time operation."""
        try:
            now = datetime.now()
            
            if operation == "now":
                return {
                    "current_datetime": now.isoformat(),
                    "current_date": now.date().isoformat(),
                    "current_time": now.time().isoformat(),
                    "timestamp": now.timestamp(),
                    "weekday": now.strftime("%A"),
                    "timezone": str(now.astimezone().tzinfo)
                }
            
            elif operation == "add_days":
                days_offset = kwargs.get("days_offset", 0)
                future_date = now + timedelta(days=days_offset)
                return {
                    "original_date": now.isoformat(),
                    "days_offset": days_offset,
                    "result_date": future_date.isoformat(),
                    "weekday": future_date.strftime("%A")
                }
            
            elif operation == "parse":
                date_string = kwargs.get("date_string", "")
                parsed_date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                return {
                    "input_string": date_string,
                    "parsed_date": parsed_date.isoformat(),
                    "weekday": parsed_date.strftime("%A"),
                    "timestamp": parsed_date.timestamp()
                }
            
            else:
                return {"error": f"Unknown operation: {operation}"}
            
        except Exception as e:
            logger.error(f"DateTime tool error: {e}")
            return {"error": str(e)}


# Function to register all default tools
def register_default_tools(registry):
    """Register all default tools with the registry."""
    tools = [
        (WebSearchTool(), "search"),
        (CalculatorTool(), "computation"),
        (TextSummarizerTool(), "data_processing"),
        (FileReaderTool(), "file_operations"),
        (JSONParserTool(), "data_processing"),
        (HTTPRequestTool(), "communication"),
        (DateTimeTool(), "general")
    ]
    
    for tool, category in tools:
        registry.register_tool(tool, category)
    
    logger.info(f"Registered {len(tools)} default tools")
