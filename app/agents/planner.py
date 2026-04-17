"""Planner Agent for daily planning and scheduling."""
import json
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agents.base import BaseAgent, AgentContext


class PlannerAgent(BaseAgent):
    """Agent for creating optimized daily schedules and plans."""
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert productivity coach and daily planner. Your role is to help users optimize their day by creating actionable, realistic schedules.

## Your Capabilities:
- Analyze tasks, priorities, and deadlines
- Consider calendar events and time blocks
- Factor in energy levels throughout the day
- Suggest optimal task ordering
- Identify potential conflicts or overcommitments
- Recommend breaks and buffer time

## Guidelines:
1. **Prioritize effectively**: Urgent + Important tasks first, then Important, then Urgent, then Others
2. **Time blocking**: Suggest specific time slots for tasks
3. **Be realistic**: Account for transition time between tasks
4. **Energy management**: Schedule demanding tasks during peak energy hours (usually morning)
5. **Include breaks**: Recommend short breaks every 90 minutes

## Context Available:
- Tasks: {tasks}
- Calendar Events: {calendar_events}
- Habits: {habits}

## Output Format:
When creating a daily plan, structure your response as:

### 🌅 Morning (6 AM - 12 PM)
[Time-blocked tasks and activities]

### ☀️ Afternoon (12 PM - 6 PM)
[Time-blocked tasks and activities]

### 🌙 Evening (6 PM - 10 PM)
[Time-blocked tasks and activities]

### 💡 Key Priorities for Today
1. [Most important task]
2. [Second priority]
3. [Third priority]

### ⚠️ Potential Conflicts
[Any scheduling conflicts or concerns]

Be encouraging but realistic. If the user has too many tasks, help them prioritize and suggest what can be deferred."""
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build the planning prompt template."""
        return ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ])
    
    async def create_daily_plan(
        self,
        context: AgentContext,
        preferences: Optional[dict] = None,
    ) -> str:
        """Create an optimized daily plan."""
        preferences = preferences or {}
        
        input_text = "Please create an optimized daily plan for today based on my tasks, calendar, and habits."
        
        if preferences.get("focus_areas"):
            input_text += f"\n\nI want to focus on: {', '.join(preferences['focus_areas'])}"
        
        if preferences.get("energy_peak"):
            input_text += f"\n\nMy peak energy time is: {preferences['energy_peak']}"
        
        return await self.run(
            input_text=input_text,
            context=context.to_dict(),
        )
    
    async def suggest_task_breakdown(
        self,
        task_title: str,
        task_description: Optional[str] = None,
    ) -> list[str]:
        """Break down a complex task into subtasks."""
        prompt = f"""Break down this task into smaller, actionable subtasks:

Task: {task_title}
{f'Description: {task_description}' if task_description else ''}

Return ONLY a JSON array of subtask titles, nothing else. Example:
["Subtask 1", "Subtask 2", "Subtask 3"]"""
        
        response = await self.run(input_text=prompt)
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            subtasks = json.loads(response)
            if isinstance(subtasks, list):
                return [str(s) for s in subtasks]
        except json.JSONDecodeError:
            lines = response.strip().split("\n")
            subtasks = []
            for line in lines:
                line = line.strip()
                if line.startswith(("-", "•", "*")):
                    line = line[1:].strip()
                if line.startswith(tuple("0123456789")):
                    line = line.split(".", 1)[-1].strip()
                    line = line.split(")", 1)[-1].strip()
                if line:
                    subtasks.append(line)
            return subtasks[:10]
        
        return []
    
    async def optimize_schedule(
        self,
        tasks: list[dict],
        events: list[dict],
        constraints: Optional[dict] = None,
    ) -> dict:
        """Optimize task scheduling around calendar events."""
        constraints = constraints or {}
        
        prompt = f"""Optimize this schedule:

Tasks to complete:
{json.dumps(tasks, indent=2)}

Fixed calendar events:
{json.dumps(events, indent=2)}

Constraints:
- Working hours: {constraints.get('working_hours', '9 AM - 5 PM')}
- Break preference: {constraints.get('break_preference', 'Every 90 minutes')}
- Focus time needed: {constraints.get('focus_time', 'Morning')}

Return a JSON object with optimized schedule:
{{
    "schedule": [
        {{"time": "9:00 AM", "duration_minutes": 60, "activity": "Task name", "type": "task|event|break"}}
    ],
    "deferred_tasks": ["Tasks that don't fit today"],
    "recommendations": ["Scheduling recommendations"]
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
                "schedule": [],
                "deferred_tasks": [],
                "recommendations": [response],
            }
