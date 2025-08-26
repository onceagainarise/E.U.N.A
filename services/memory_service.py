"""Memory service using Pinecone for EUNA MVP."""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import json
from datetime import datetime

try:
    import pinecone
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logging.warning("Pinecone not available, using fallback memory service")

from config.settings import settings
from services.database_service import db_service

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing semantic memory using Pinecone vector database."""
    
    def __init__(self):
        self.index = None
        self.dimension = 1536  # Standard embedding dimension
        self.fallback_memory = {}  # In-memory fallback
        
        if PINECONE_AVAILABLE:
            try:
                self._initialize_pinecone()
            except Exception as e:
                logger.warning(f"Failed to initialize Pinecone: {e}. Using fallback memory.")
                PINECONE_AVAILABLE = False
    
    def _initialize_pinecone(self):
        """Initialize Pinecone connection and index."""
        if not PINECONE_AVAILABLE:
            return
            
        try:
            # Initialize Pinecone
            pc = Pinecone(api_key=settings.pinecone_api_key)
            
            # Check if index exists, create if not
            index_name = settings.pinecone_index_name
            existing_indexes = pc.list_indexes().names()
            
            if index_name not in existing_indexes:
                pc.create_index(
                    name=index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=settings.pinecone_environment
                    )
                )
                logger.info(f"Created Pinecone index: {index_name}")
            
            self.index = pc.Index(index_name)
            logger.info("Pinecone memory service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone: {e}")
            raise
    
    async def store_memory(self, content: str, content_type: str, 
                          metadata: Optional[Dict] = None, task_id: Optional[int] = None) -> str:
        """Store content in memory with semantic embedding."""
        
        # Generate unique ID for the memory
        memory_id = hashlib.md5(f"{content}{datetime.utcnow().isoformat()}".encode()).hexdigest()
        
        # Create embedding (simplified - in production, use actual embedding model)
        embedding = await self._create_embedding(content)
        
        # Prepare metadata
        full_metadata = {
            "content_type": content_type,
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            **(metadata or {})
        }
        
        try:
            if PINECONE_AVAILABLE and self.index:
                # Store in Pinecone
                self.index.upsert(
                    vectors=[(memory_id, embedding, full_metadata)]
                )
                logger.info(f"Stored memory in Pinecone: {memory_id}")
            else:
                # Fallback to in-memory storage
                self.fallback_memory[memory_id] = {
                    "content": content,
                    "embedding": embedding,
                    "metadata": full_metadata
                }
                logger.info(f"Stored memory in fallback: {memory_id}")
            
            # Also store in database for persistence
            await db_service.create_memory_entry(
                content=content,
                content_type=content_type,
                metadata=full_metadata,
                embedding_id=memory_id
            )
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise
    
    async def search_memory(self, query: str, content_type: Optional[str] = None, 
                           limit: int = 5, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """Search memory using semantic similarity."""
        
        try:
            # Create query embedding
            query_embedding = await self._create_embedding(query)
            
            if PINECONE_AVAILABLE and self.index:
                # Search in Pinecone
                filter_dict = {"content_type": content_type} if content_type else {}
                
                search_results = self.index.query(
                    vector=query_embedding,
                    top_k=limit,
                    include_metadata=True,
                    filter=filter_dict
                )
                
                results = []
                for match in search_results.matches:
                    if match.score >= min_score:
                        # Get full content from database
                        memory_entry = await db_service.get_memory_entries()
                        content = next((m.content for m in memory_entry if m.embedding_id == match.id), "")
                        
                        results.append({
                            "id": match.id,
                            "content": content,
                            "score": match.score,
                            "metadata": match.metadata
                        })
                
                logger.info(f"Found {len(results)} relevant memories in Pinecone")
                return results
                
            else:
                # Fallback search (simple similarity)
                results = []
                for memory_id, memory_data in self.fallback_memory.items():
                    if content_type and memory_data["metadata"].get("content_type") != content_type:
                        continue
                    
                    # Simple cosine similarity
                    similarity = self._cosine_similarity(query_embedding, memory_data["embedding"])
                    if similarity >= min_score:
                        results.append({
                            "id": memory_id,
                            "content": memory_data["content"],
                            "score": similarity,
                            "metadata": memory_data["metadata"]
                        })
                
                # Sort by score and limit
                results.sort(key=lambda x: x["score"], reverse=True)
                results = results[:limit]
                
                logger.info(f"Found {len(results)} relevant memories in fallback")
                return results
                
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []
    
    async def get_context_for_task(self, task_description: str, task_id: Optional[int] = None) -> Dict[str, Any]:
        """Get relevant context for a task from memory."""
        
        # Search for relevant memories
        relevant_memories = await self.search_memory(task_description, limit=10)
        
        # Get task-specific memories if task_id provided
        task_memories = []
        if task_id:
            task_memories = await self.search_memory(
                task_description, 
                content_type="task_result",
                limit=5
            )
        
        # Get user preferences
        preference_memories = await self.search_memory(
            task_description,
            content_type="user_preference",
            limit=3
        )
        
        return {
            "relevant_memories": relevant_memories,
            "task_memories": task_memories,
            "user_preferences": preference_memories,
            "context_summary": self._summarize_context(relevant_memories + task_memories + preference_memories)
        }
    
    async def store_task_result(self, task_id: int, task_description: str, result: Dict[str, Any]):
        """Store task result for future reference."""
        
        content = f"Task: {task_description}\nResult: {json.dumps(result, indent=2)}"
        
        await self.store_memory(
            content=content,
            content_type="task_result",
            metadata={
                "task_id": task_id,
                "task_description": task_description,
                "success": result.get("success", True)
            },
            task_id=task_id
        )
    
    async def store_user_preference(self, preference_type: str, preference_data: Dict[str, Any]):
        """Store user preference for future tasks."""
        
        content = f"User preference for {preference_type}: {json.dumps(preference_data, indent=2)}"
        
        await self.store_memory(
            content=content,
            content_type="user_preference",
            metadata={
                "preference_type": preference_type,
                **preference_data
            }
        )
    
    async def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for text (simplified implementation)."""
        
        # In production, use actual embedding model like OpenAI embeddings
        # For MVP, create a simple hash-based embedding
        import hashlib
        
        # Create a deterministic "embedding" based on text hash
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Convert hash to float vector
        embedding = []
        for i in range(0, min(len(text_hash), self.dimension * 8), 8):
            chunk = text_hash[i:i+8]
            if len(chunk) == 8:
                # Convert hex to float between -1 and 1
                value = int(chunk, 16) / (16**8) * 2 - 1
                embedding.append(value)
        
        # Pad or truncate to correct dimension
        while len(embedding) < self.dimension:
            embedding.append(0.0)
        embedding = embedding[:self.dimension]
        
        return embedding
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _summarize_context(self, memories: List[Dict[str, Any]]) -> str:
        """Summarize context from memories."""
        
        if not memories:
            return "No relevant context found."
        
        summary_parts = []
        for memory in memories[:5]:  # Limit to top 5 memories
            content = memory.get("content", "")[:200]  # Truncate long content
            score = memory.get("score", 0)
            summary_parts.append(f"• {content} (relevance: {score:.2f})")
        
        return "Relevant context:\n" + "\n".join(summary_parts)


# Global memory service instance
memory_service = MemoryService()
