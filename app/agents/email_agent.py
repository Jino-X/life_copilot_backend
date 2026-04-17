"""Email Agent for email analysis and reply generation."""
import json
from typing import Optional

from app.agents.base import BaseAgent


class EmailAgent(BaseAgent):
    """Agent for email summarization, categorization, and reply generation."""
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert email assistant. Your role is to help users manage their emails efficiently by:

## Your Capabilities:
1. **Summarizing emails**: Extract key points and action items
2. **Categorizing emails**: Classify as important, follow-up, newsletter, spam, personal, work
3. **Generating replies**: Write professional, context-appropriate responses
4. **Identifying urgency**: Assess priority level (1-5, where 5 is most urgent)

## Guidelines:
- Be concise but thorough in summaries
- Match the tone of replies to the original email
- Identify action items clearly
- Flag time-sensitive content
- Maintain professionalism while being personable

## For Reply Generation:
- Keep replies focused and actionable
- Include appropriate greetings and sign-offs
- Address all points raised in the original email
- Suggest follow-up actions when appropriate"""
    
    async def analyze_email(
        self,
        subject: str,
        sender: str,
        content: str,
    ) -> dict:
        """Analyze an email and return structured analysis."""
        prompt = f"""Analyze this email and provide a structured analysis:

From: {sender}
Subject: {subject}

Content:
{content}

Return a JSON object with:
{{
    "summary": "Brief 1-2 sentence summary",
    "category": "important|follow_up|newsletter|spam|personal|work|other",
    "priority_score": 1-5,
    "action_items": ["List of action items if any"],
    "key_points": ["Main points from the email"],
    "sentiment": "positive|neutral|negative",
    "requires_response": true/false,
    "suggested_response_tone": "formal|casual|urgent"
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
                "summary": response[:200],
                "category": "other",
                "priority_score": 3,
                "action_items": [],
                "key_points": [],
                "sentiment": "neutral",
                "requires_response": True,
                "suggested_response_tone": "formal",
            }
    
    async def generate_reply(
        self,
        subject: str,
        sender: str,
        content: str,
        tone: str = "professional",
        key_points: Optional[list[str]] = None,
        user_name: Optional[str] = None,
    ) -> str:
        """Generate a reply to an email."""
        key_points_text = ""
        if key_points:
            key_points_text = f"\n\nKey points to address:\n" + "\n".join(f"- {p}" for p in key_points)
        
        prompt = f"""Generate a {tone} reply to this email:

From: {sender}
Subject: {subject}

Original Email:
{content}
{key_points_text}

Requirements:
- Tone: {tone}
- Be concise but address all relevant points
- Include appropriate greeting and sign-off
{f'- Sign off as: {user_name}' if user_name else ''}

Write ONLY the reply email, nothing else."""
        
        return await self.run(input_text=prompt)
    
    async def categorize_emails(
        self,
        emails: list[dict],
    ) -> list[dict]:
        """Categorize multiple emails at once."""
        email_summaries = []
        for i, email in enumerate(emails):
            email_summaries.append(
                f"{i+1}. From: {email.get('sender', 'Unknown')}\n"
                f"   Subject: {email.get('subject', 'No Subject')}\n"
                f"   Preview: {email.get('snippet', '')[:100]}"
            )
        
        prompt = f"""Categorize these emails:

{chr(10).join(email_summaries)}

Return a JSON array with category and priority for each:
[
    {{"index": 1, "category": "important|follow_up|newsletter|spam|personal|work|other", "priority": 1-5}},
    ...
]"""
        
        response = await self.run(input_text=prompt)
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            return json.loads(response)
        except json.JSONDecodeError:
            return [{"index": i+1, "category": "other", "priority": 3} for i in range(len(emails))]
    
    async def summarize_thread(
        self,
        emails: list[dict],
    ) -> dict:
        """Summarize an email thread."""
        thread_content = []
        for email in emails:
            thread_content.append(
                f"From: {email.get('sender', 'Unknown')}\n"
                f"Date: {email.get('date', 'Unknown')}\n"
                f"Content: {email.get('content', email.get('snippet', ''))}\n"
                f"---"
            )
        
        prompt = f"""Summarize this email thread:

{chr(10).join(thread_content)}

Return a JSON object:
{{
    "summary": "Overall thread summary",
    "participants": ["List of participants"],
    "key_decisions": ["Any decisions made"],
    "pending_actions": ["Outstanding action items"],
    "current_status": "Brief status of the conversation"
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
                "summary": response[:500],
                "participants": [],
                "key_decisions": [],
                "pending_actions": [],
                "current_status": "Unknown",
            }
