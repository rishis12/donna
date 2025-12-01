from openai import AsyncOpenAI
from typing import Optional
import json
from ..core.config import get_settings

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a helpful AI assistant that helps users manage their schedule, reminders, and emails.
Parse the user's request and return a structured JSON response with the following format:
{
    "intent": "create_reminder" | "schedule_event" | "move_event" | "draft_email" | "send_email" | "get_schedule" | "small_talk",
    "entities": {
        "time": "ISO datetime string or relative time description",
        "date": "date string",
        "attendees": ["list of email addresses or names"],
        "subject": "email or event subject",
        "body": "email body or event description",
        "reminder_text": "reminder content",
        "event_title": "calendar event title",
        "duration_minutes": 30
    },
    "response": "Natural language response to the user",
    "requires_confirmation": true/false
}

For times, try to parse them into specific times. If the user says "tomorrow morning", interpret it as 9:00 AM the next day.
If the user says "3pm", use today's date at 15:00.
Always be helpful and confirm you understood the request correctly."""

async def parse_utterance(utterance: str, current_time: str) -> dict:
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Current time: {current_time}\n\nUser request: {utterance}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1000
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        return {
            "intent": "small_talk",
            "entities": {},
            "response": f"I'm sorry, I had trouble understanding that. Could you try again?",
            "requires_confirmation": False,
            "error": str(e)
        }

async def draft_email_content(to: str, subject_hint: str, context: str) -> dict:
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an email drafting assistant. Write professional, clear emails."},
                {"role": "user", "content": f"Draft an email to {to}. Context: {context}. Subject hint: {subject_hint}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1000
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"subject": subject_hint, "body": context, "error": str(e)}

async def transcribe_audio(audio_data: bytes) -> str:
    try:
        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.webm", audio_data, "audio/webm")
        )
        return transcription.text
    except Exception as e:
        return f"Error transcribing audio: {str(e)}"

