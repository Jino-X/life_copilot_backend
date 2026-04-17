"""Memory Agent for long-term context and recall."""
import json
from typing import Optional

from app.agents.base import BaseAgent
from app.services.vector_store import VectorStoreService


class MemoryAgent(BaseAgent):
    """Agent for storing and retrieving long-term user context."""
    
    def __init__(self, vector_store: VectorStoreService, **kwargs):
        super().__init__(**kwargs)
        self.vector_store = vector_store
    
    @property
    def system_prompt(self) -> str:
        return """You are a memory and context management assistant. Your role is to:

## Capabilities:
1. **Extract key information**: Identify important facts, preferences, and patterns from conversations
2. **Recall relevant context**: Retrieve and present relevant past information
3. **Synthesize memories**: Combine multiple memories into coherent context
4. **Identify patterns**: Recognize user habits, preferences, and recurring themes

## Guidelines:
- Extract factual, useful information only
- Avoid storing sensitive personal data unnecessarily
- Prioritize actionable and preference-related information
- Connect related memories when relevant
- Present recalled information naturally in conversation

## Information to Remember:
- User preferences and habits
- Important dates and events
- Goals and aspirations
- Work/project context
- Relationships and contacts mentioned
- Recurring tasks or patterns"""
    
    async def extract_memories(
        self,
        conversation: str,
        existing_context: Optional[str] = None,
    ) -> list[dict]:
        """Extract memorable information from a conversation."""
        prompt = f"""Analyze this conversation and extract key information worth remembering:

Conversation:
{conversation}

{f'Existing context: {existing_context}' if existing_context else ''}

Return a JSON array of memories to store:
[
    {{
        "content": "The specific information to remember",
        "category": "preference|goal|fact|relationship|habit|project",
        "importance": "high|medium|low",
        "keywords": ["relevant", "keywords"]
    }}
]

Only extract genuinely useful information. Return empty array if nothing notable."""
        
        response = await self.run(input_text=prompt)
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            memories = json.loads(response)
            return memories if isinstance(memories, list) else []
        except json.JSONDecodeError:
            return []
    
    async def store_memory(
        self,
        user_id: int,
        content: str,
        category: str = "general",
        metadata: Optional[dict] = None,
    ) -> str:
        """Store a memory in the vector store."""
        full_metadata = {
            "category": category,
            **(metadata or {}),
        }
        
        embedding_id = await self.vector_store.add_document(
            content=content,
            user_id=user_id,
            doc_type="memory",
            doc_id=0,
            metadata=full_metadata,
        )
        
        return embedding_id
    
    async def recall_memories(
        self,
        user_id: int,
        query: str,
        k: int = 5,
    ) -> list[dict]:
        """Recall relevant memories based on a query."""
        results = await self.vector_store.search(
            query=query,
            user_id=user_id,
            doc_type="memory",
            k=k,
        )
        
        return results
    
    async def synthesize_context(
        self,
        memories: list[dict],
        current_query: str,
    ) -> str:
        """Synthesize multiple memories into coherent context."""
        if not memories:
            return ""
        
        memories_text = "\n".join(
            f"- {m.get('content', '')}" for m in memories
        )
        
        prompt = f"""Synthesize these memories into relevant context for the current query:

Memories:
{memories_text}

Current Query: {current_query}

Create a brief, coherent summary of relevant context (2-3 sentences max).
Only include information directly relevant to the query.
If no memories are relevant, respond with "No relevant context found." """
        
        return await self.run(input_text=prompt)
    
    async def get_user_profile_summary(
        self,
        user_id: int,
    ) -> dict:
        """Generate a summary of what we know about the user."""
        memories = await self.vector_store.get_user_memories(user_id, limit=20)
        
        if not memories:
            return {
                "summary": "No stored information about this user yet.",
                "preferences": [],
                "goals": [],
                "patterns": [],
            }
        
        memories_text = "\n".join(
            f"- {m.get('content', '')}" for m in memories
        )
        
        prompt = f"""Based on these stored memories, create a user profile summary:

Memories:
{memories_text}

Return a JSON object:
{{
    "summary": "Brief overall summary of the user",
    "preferences": ["List of known preferences"],
    "goals": ["Known goals or aspirations"],
    "patterns": ["Observed patterns or habits"],
    "key_facts": ["Important facts about the user"]
}}"""
        
        response = await self.run(input_text=prompt)
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "summary": response[:300],
                "preferences": [],
                "goals": [],
                "patterns": [],
            }
    
    async def should_remember(
        self,
        message: str,
    ) -> bool:
        """Determine if a message contains information worth remembering."""
        prompt = f"""Analyze this message and determine if it contains information worth storing in long-term memory:

Message: {message}

Information worth remembering includes:
- User preferences
- Goals or aspirations
- Important facts about their life/work
- Recurring patterns or habits
- Significant events or dates

Respond with ONLY "yes" or "no"."""
        
        response = await self.run(input_text=prompt)
        return response.strip().lower() == "yes"
