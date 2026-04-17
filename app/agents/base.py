"""Base agent class and utilities."""
from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        streaming: bool = True,
    ):
        self.model_name = model or settings.OPENAI_MODEL
        self.temperature = temperature
        self.streaming = streaming
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            streaming=self.streaming,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        
        self.tools: list[BaseTool] = []
        self._setup_tools()
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @property
    def name(self) -> str:
        """Return the agent name."""
        return self.__class__.__name__
    
    def _setup_tools(self) -> None:
        """Setup tools for this agent. Override in subclasses."""
        pass
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build the chat prompt template."""
        return ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ])
    
    def _format_chat_history(
        self,
        messages: list[dict],
    ) -> list[BaseMessage]:
        """Format chat history for the prompt."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                formatted.append(HumanMessage(content=content))
            elif role == "assistant":
                formatted.append(AIMessage(content=content))
            elif role == "system":
                formatted.append(SystemMessage(content=content))
        
        return formatted
    
    async def run(
        self,
        input_text: str,
        chat_history: Optional[list[dict]] = None,
        context: Optional[dict] = None,
    ) -> str:
        """Run the agent with the given input."""
        chat_history = chat_history or []
        context = context or {}
        
        prompt = self._build_prompt()
        formatted_history = self._format_chat_history(chat_history)
        
        chain = prompt | self.llm
        
        try:
            response = await chain.ainvoke({
                "input": input_text,
                "chat_history": formatted_history,
                **context,
            })
            return response.content
        except Exception as e:
            logger.error(f"Agent {self.name} error: {e}")
            raise
    
    async def stream(
        self,
        input_text: str,
        chat_history: Optional[list[dict]] = None,
        context: Optional[dict] = None,
    ):
        """Stream the agent response."""
        chat_history = chat_history or []
        context = context or {}
        
        prompt = self._build_prompt()
        formatted_history = self._format_chat_history(chat_history)
        
        chain = prompt | self.llm
        
        try:
            async for chunk in chain.astream({
                "input": input_text,
                "chat_history": formatted_history,
                **context,
            }):
                if hasattr(chunk, "content"):
                    yield chunk.content
        except Exception as e:
            logger.error(f"Agent {self.name} streaming error: {e}")
            raise


class AgentContext:
    """Context object passed to agents containing user data."""
    
    def __init__(
        self,
        user_id: int,
        tasks: Optional[list[dict]] = None,
        calendar_events: Optional[list[dict]] = None,
        notes: Optional[list[dict]] = None,
        habits: Optional[list[dict]] = None,
        memories: Optional[list[dict]] = None,
    ):
        self.user_id = user_id
        self.tasks = tasks or []
        self.calendar_events = calendar_events or []
        self.notes = notes or []
        self.habits = habits or []
        self.memories = memories or []
    
    def to_dict(self) -> dict:
        """Convert context to dictionary for prompt."""
        return {
            "tasks": self._format_tasks(),
            "calendar_events": self._format_events(),
            "notes": self._format_notes(),
            "habits": self._format_habits(),
            "memories": self._format_memories(),
        }
    
    def _format_tasks(self) -> str:
        if not self.tasks:
            return "No tasks."
        
        lines = []
        for task in self.tasks:
            status = "✓" if task.get("status") == "completed" else "○"
            priority = task.get("priority", "medium")
            due = task.get("due_date", "No due date")
            lines.append(f"{status} [{priority}] {task['title']} (Due: {due})")
        
        return "\n".join(lines)
    
    def _format_events(self) -> str:
        if not self.calendar_events:
            return "No upcoming events."
        
        lines = []
        for event in self.calendar_events:
            start = event.get("start_time", "")
            lines.append(f"• {event['title']} at {start}")
        
        return "\n".join(lines)
    
    def _format_notes(self) -> str:
        if not self.notes:
            return "No relevant notes."
        
        lines = []
        for note in self.notes:
            preview = note.get("content", "")[:100]
            lines.append(f"• {note['title']}: {preview}...")
        
        return "\n".join(lines)
    
    def _format_habits(self) -> str:
        if not self.habits:
            return "No habits tracked."
        
        lines = []
        for habit in self.habits:
            streak = habit.get("current_streak", 0)
            completed = "✓" if habit.get("completed_today") else "○"
            lines.append(f"{completed} {habit['name']} (Streak: {streak} days)")
        
        return "\n".join(lines)
    
    def _format_memories(self) -> str:
        if not self.memories:
            return "No relevant memories."
        
        lines = []
        for memory in self.memories:
            lines.append(f"• {memory.get('content', '')[:150]}...")
        
        return "\n".join(lines)
