"""Reminder Agent for task reminders and nudges."""
import json
from datetime import datetime, timezone
from typing import Optional

from app.agents.base import BaseAgent, AgentContext


class ReminderAgent(BaseAgent):
    """Agent for generating reminders and productivity nudges."""
    
    @property
    def system_prompt(self) -> str:
        return """You are a supportive productivity assistant focused on helping users stay on track with their tasks and goals.

## Your Role:
- Generate timely, helpful reminders
- Provide motivational nudges without being annoying
- Help users prioritize when overwhelmed
- Celebrate progress and completions
- Suggest when to take breaks

## Guidelines:
1. **Be supportive, not nagging**: Encourage rather than pressure
2. **Context-aware**: Consider time of day, workload, and patterns
3. **Actionable**: Always suggest a specific next step
4. **Personalized**: Reference specific tasks and deadlines
5. **Balanced**: Mix reminders with encouragement

## Tone:
- Friendly and supportive
- Professional but warm
- Motivating without being pushy
- Understanding of challenges"""
    
    async def generate_reminder(
        self,
        task: dict,
        urgency_level: str = "normal",
    ) -> str:
        """Generate a reminder for a specific task."""
        prompt = f"""Generate a {urgency_level} reminder for this task:

Task: {task.get('title')}
Description: {task.get('description', 'No description')}
Due: {task.get('due_date', 'No due date')}
Priority: {task.get('priority', 'medium')}

Create a brief, encouraging reminder message (2-3 sentences max)."""
        
        return await self.run(input_text=prompt)
    
    async def generate_daily_nudge(
        self,
        context: AgentContext,
        time_of_day: str = "morning",
    ) -> str:
        """Generate a daily productivity nudge."""
        prompt = f"""Generate a {time_of_day} productivity nudge based on:

Tasks: {context._format_tasks()}
Habits: {context._format_habits()}
Events: {context._format_events()}

Create a brief, motivating message that:
1. Acknowledges the current time of day
2. Highlights 1-2 key priorities
3. Provides encouragement
4. Suggests a specific action

Keep it under 100 words."""
        
        return await self.run(input_text=prompt)
    
    async def analyze_overdue_tasks(
        self,
        overdue_tasks: list[dict],
    ) -> dict:
        """Analyze overdue tasks and suggest actions."""
        if not overdue_tasks:
            return {
                "message": "Great job! You have no overdue tasks.",
                "suggestions": [],
            }
        
        tasks_text = "\n".join(
            f"- {t.get('title')} (Due: {t.get('due_date')}, Priority: {t.get('priority')})"
            for t in overdue_tasks
        )
        
        prompt = f"""Analyze these overdue tasks and provide guidance:

Overdue Tasks:
{tasks_text}

Return a JSON object:
{{
    "message": "Brief empathetic message about the situation",
    "priority_order": ["Tasks in recommended order to tackle"],
    "suggestions": [
        {{"task": "Task name", "suggestion": "Specific suggestion for this task"}}
    ],
    "quick_wins": ["Tasks that could be completed quickly"],
    "consider_deferring": ["Tasks that might be okay to reschedule"]
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
                "message": response[:200],
                "suggestions": [],
            }
    
    async def suggest_break(
        self,
        work_duration_minutes: int,
        current_task: Optional[str] = None,
    ) -> str:
        """Suggest a break based on work duration."""
        prompt = f"""The user has been working for {work_duration_minutes} minutes{f' on "{current_task}"' if current_task else ''}.

Generate a brief, friendly break suggestion that:
1. Acknowledges their effort
2. Suggests a specific break activity
3. Recommends break duration
4. Encourages returning refreshed

Keep it under 50 words."""
        
        return await self.run(input_text=prompt)
    
    async def celebrate_completion(
        self,
        task: dict,
        streak_info: Optional[dict] = None,
    ) -> str:
        """Generate a celebration message for task completion."""
        prompt = f"""The user just completed a task:

Task: {task.get('title')}
Priority: {task.get('priority', 'medium')}
{f"This is day {streak_info.get('current_streak')} of their streak!" if streak_info else ""}

Generate a brief, celebratory message (1-2 sentences) that:
1. Congratulates them
2. Acknowledges the accomplishment
3. Motivates continued progress

Be genuine and not over-the-top."""
        
        return await self.run(input_text=prompt)
    
    async def generate_habit_reminder(
        self,
        habit: dict,
        time_remaining: Optional[str] = None,
    ) -> str:
        """Generate a reminder for a habit."""
        prompt = f"""Generate a reminder for this habit:

Habit: {habit.get('name')}
Current Streak: {habit.get('current_streak', 0)} days
Target: {habit.get('target_count', 1)} times per {habit.get('frequency', 'day')}
{f'Time remaining today: {time_remaining}' if time_remaining else ''}

Create a brief, encouraging reminder (1-2 sentences) that:
1. Mentions the habit
2. References the streak if applicable
3. Motivates action

Don't be pushy."""
        
        return await self.run(input_text=prompt)
