"""Orchestrator Agent - Main agent that coordinates all other agents."""
import json
from typing import AsyncGenerator, Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agents.base import BaseAgent, AgentContext
from app.agents.planner import PlannerAgent
from app.agents.email_agent import EmailAgent
from app.agents.reminder import ReminderAgent
from app.agents.memory import MemoryAgent
from app.services.vector_store import VectorStoreService
from app.core.logging import get_logger

logger = get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """Main agent that orchestrates all specialized agents."""
    
    def __init__(
        self,
        vector_store: VectorStoreService,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.vector_store = vector_store
        
        self.planner = PlannerAgent()
        self.email_agent = EmailAgent()
        self.reminder = ReminderAgent()
        self.memory = MemoryAgent(vector_store)
    
    @property
    def system_prompt(self) -> str:
        return """You are a helpful AI Life Copilot assistant. You help users manage their daily life including tasks, calendar, emails, notes, and habits.

## Your Capabilities:
1. **Task Management**: Create, update, and organize tasks. Break down complex tasks into subtasks.
2. **Calendar**: View and manage calendar events. Suggest optimal scheduling.
3. **Email**: Summarize emails, generate replies, categorize messages.
4. **Notes**: Create and search notes. Recall relevant information.
5. **Habits**: Track habits, view streaks, provide encouragement.
6. **Planning**: Create daily plans, optimize schedules, prioritize tasks.

## Context Available:
- Tasks: {tasks}
- Calendar Events: {calendar_events}
- Habits: {habits}
- Relevant Memories: {memories}

## Guidelines:
1. Be helpful, concise, and actionable
2. Use the context provided to give personalized responses
3. When asked to do something, confirm the action taken
4. Proactively suggest improvements when appropriate
5. Be encouraging about progress and achievements
6. Ask clarifying questions when needed

## Response Style:
- Be conversational but efficient
- Use bullet points for lists
- Highlight important information
- Include specific details from context when relevant"""
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build the orchestrator prompt template."""
        return ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ])
    
    async def process_message(
        self,
        message: str,
        user_id: int,
        context: AgentContext,
        chat_history: Optional[list[dict]] = None,
    ) -> str:
        """Process a user message and return a response."""
        chat_history = chat_history or []
        
        relevant_memories = await self.memory.recall_memories(
            user_id=user_id,
            query=message,
            k=3,
        )
        context.memories = relevant_memories
        
        intent = await self._classify_intent(message)
        
        if intent == "planning":
            response = await self._handle_planning(message, context, chat_history)
        elif intent == "email":
            response = await self._handle_email(message, context, chat_history)
        elif intent == "task":
            response = await self._handle_task(message, context, chat_history)
        else:
            response = await self.run(
                input_text=message,
                chat_history=chat_history,
                context=context.to_dict(),
            )
        
        if await self.memory.should_remember(message):
            memories = await self.memory.extract_memories(
                conversation=f"User: {message}\nAssistant: {response}",
            )
            for mem in memories:
                await self.memory.store_memory(
                    user_id=user_id,
                    content=mem.get("content", ""),
                    category=mem.get("category", "general"),
                    metadata={"keywords": mem.get("keywords", [])},
                )
        
        return response
    
    async def stream_message(
        self,
        message: str,
        user_id: int,
        context: AgentContext,
        chat_history: Optional[list[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response to a user message."""
        chat_history = chat_history or []
        
        relevant_memories = await self.memory.recall_memories(
            user_id=user_id,
            query=message,
            k=3,
        )
        context.memories = relevant_memories
        
        full_response = ""
        async for chunk in self.stream(
            input_text=message,
            chat_history=chat_history,
            context=context.to_dict(),
        ):
            full_response += chunk
            yield chunk
        
        if await self.memory.should_remember(message):
            memories = await self.memory.extract_memories(
                conversation=f"User: {message}\nAssistant: {full_response}",
            )
            for mem in memories:
                await self.memory.store_memory(
                    user_id=user_id,
                    content=mem.get("content", ""),
                    category=mem.get("category", "general"),
                )
    
    async def _classify_intent(self, message: str) -> str:
        """Classify the user's intent."""
        message_lower = message.lower()
        
        planning_keywords = ["plan", "schedule", "organize", "prioritize", "today", "tomorrow", "week"]
        email_keywords = ["email", "mail", "reply", "respond", "inbox", "message"]
        task_keywords = ["task", "todo", "break down", "subtask", "deadline", "due"]
        
        if any(kw in message_lower for kw in planning_keywords):
            return "planning"
        elif any(kw in message_lower for kw in email_keywords):
            return "email"
        elif any(kw in message_lower for kw in task_keywords):
            return "task"
        
        return "general"
    
    async def _handle_planning(
        self,
        message: str,
        context: AgentContext,
        chat_history: list[dict],
    ) -> str:
        """Handle planning-related requests."""
        if "plan my day" in message.lower() or "daily plan" in message.lower():
            return await self.planner.create_daily_plan(context)
        
        return await self.run(
            input_text=message,
            chat_history=chat_history,
            context=context.to_dict(),
        )
    
    async def _handle_email(
        self,
        message: str,
        context: AgentContext,
        chat_history: list[dict],
    ) -> str:
        """Handle email-related requests."""
        return await self.run(
            input_text=message,
            chat_history=chat_history,
            context=context.to_dict(),
        )
    
    async def _handle_task(
        self,
        message: str,
        context: AgentContext,
        chat_history: list[dict],
    ) -> str:
        """Handle task-related requests."""
        if "break" in message.lower() and ("down" in message.lower() or "into" in message.lower()):
            import re
            match = re.search(r'["\'](.+?)["\']', message)
            if match:
                task_title = match.group(1)
                subtasks = await self.planner.suggest_task_breakdown(task_title)
                if subtasks:
                    return f"Here's how I'd break down '{task_title}':\n\n" + "\n".join(
                        f"{i+1}. {st}" for i, st in enumerate(subtasks)
                    )
        
        return await self.run(
            input_text=message,
            chat_history=chat_history,
            context=context.to_dict(),
        )
    
    async def get_daily_summary(
        self,
        context: AgentContext,
    ) -> dict:
        """Generate a daily summary."""
        plan = await self.planner.create_daily_plan(context)
        
        nudge = await self.reminder.generate_daily_nudge(
            context=context,
            time_of_day="morning",
        )
        
        return {
            "plan": plan,
            "nudge": nudge,
            "tasks_count": len(context.tasks),
            "events_count": len(context.calendar_events),
            "habits_count": len(context.habits),
        }
