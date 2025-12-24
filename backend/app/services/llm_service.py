from groq import Groq
import json
from ..core.config import get_settings

settings = get_settings()
client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You are Donna, a witty executive assistant (like Donna from Suits). Help users manage calendar, reminders, and emails.

ALWAYS return valid JSON. For MULTIPLE actions, use the "actions" array:
{
  "actions": [
    {
      "intent": "move_event|schedule_event|cancel_event|create_reminder|etc",
      "entities": {"event_id": "...", "time": "...", "event_title": "..."}
    },
    {
      "intent": "move_event",
      "entities": {"event_id": "...", "time": "..."}
    }
  ],
  "response": "Your summary of all actions",
  "requires_confirmation": true
}

For SINGLE actions (most common):
{
  "intent": "schedule_event|move_event|update_event|cancel_event|create_reminder|list_reminders|draft_email|send_email|get_schedule|small_talk",
  "entities": {
    "time": "ISO datetime (2024-12-22T14:00:00)",
    "event_title": "meeting title",
    "event_id": "calendar event ID",
    "event_ids": ["multiple IDs"],
    "attendees": ["email@example.com"],
    "reminder_text": "reminder content",
    "duration_minutes": 30
  },
  "response": "Your response",
  "requires_confirmation": true
}

RULES:
1. For MULTIPLE actions (move my 4pm to 5pm AND my 6pm to 7pm), use the "actions" array
2. requires_confirmation = TRUE when ready to execute, FALSE when asking questions
3. Parse times relative to current time provided
4. For event operations, use the event_id from the calendar list

EXAMPLES:

Single action:
{"intent":"schedule_event","entities":{"event_title":"Team Sync","time":"2024-12-22T14:00:00"},"response":"I'll schedule 'Team Sync' for tomorrow at 2pm. Say the word!","requires_confirmation":true}

Multiple actions (rescheduling chain):
{"actions":[{"intent":"move_event","entities":{"event_id":"abc123","time":"2024-12-21T17:00:00"}},{"intent":"move_event","entities":{"event_id":"def456","time":"2024-12-21T19:00:00"}}],"response":"I'll move your 4pm to 5pm and your 6pm to 7pm. Say the word!","requires_confirmation":true}

IMPORTANT: Return ONLY raw JSON. No markdown, no explanation."""

async def parse_utterance(utterance: str, current_time: str, conversation_history: list = None, timezone: str = "UTC", calendar_context: str = "") -> dict:
    # Quick responses for simple greetings (avoid API call)
    simple_greetings = ['hi', 'hello', 'hey', 'yo', 'sup', 'hiya', 'heya']
    if utterance.lower().strip() in simple_greetings:
        return {
            "intent": "small_talk",
            "entities": {},
            "response": "Hey! What can I do for you?",
            "requires_confirmation": False
        }
    
    thanks_phrases = ['thanks', 'thank you', 'thx', 'ty', 'appreciate it']
    if utterance.lower().strip() in thanks_phrases:
        return {
            "intent": "small_talk",
            "entities": {},
            "response": "Anytime! What else do you need?",
            "requires_confirmation": False
        }
    
    try:
        time_context = f"\n\nCurrent time: {current_time}\nUser's timezone: {timezone}\nALWAYS express times in the user's timezone ({timezone}), not UTC."
        full_context = SYSTEM_PROMPT + time_context + calendar_context
        messages = [
            {"role": "system", "content": full_context}
        ]
        
        # Add conversation history (last 5 exchanges) - formatted as context
        if conversation_history:
            for msg in conversation_history[-5:]:
                # Format previous exchanges simply
                messages.append({"role": "user", "content": msg["user"]})
                # Previous assistant responses should be the JSON they returned
                messages.append({"role": "assistant", "content": json.dumps({
                    "intent": "small_talk",
                    "entities": {},
                    "response": msg["assistant"],
                    "requires_confirmation": False
                })})
        
        # Add current user message
        messages.append({"role": "user", "content": utterance})
        
        print(f"[LLM] Sending request for: '{utterance}'")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.5,  # Lower temperature for more consistent JSON
            max_tokens=1000
        )
        
        text = response.choices[0].message.content.strip()
        print(f"[LLM] Raw response: {text[:300]}...")
        
        # Clean up response if it has markdown code blocks
        if '```' in text:
            # Extract content between code blocks
            parts = text.split('```')
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith('json'):
                    text = text[4:]
                text = text.strip()
        
        # Try to find JSON in the response if it's not pure JSON
        if not text.startswith('{'):
            # Look for JSON object in the text
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]
        
        result = json.loads(text)
        print(f"[LLM] Parsed intent: {result.get('intent')}")
        return result
    except json.JSONDecodeError as e:
        print(f"[LLM] JSON Parse Error: {e}")
        print(f"[LLM] Raw text was: {text[:500] if 'text' in dir() else 'N/A'}")
        return {
            "intent": "small_talk",
            "entities": {},
            "response": "I had a bit of trouble there. Could you rephrase that?",
            "requires_confirmation": False
        }
    except Exception as e:
        print(f"[LLM] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "intent": "small_talk",
            "entities": {},
            "response": f"Something went wrong on my end. Try again?",
            "requires_confirmation": False,
            "error": str(e)
        }

async def draft_email_content(to: str, subject_hint: str, context: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an email drafting assistant. Write professional, clear emails. Return JSON with 'subject' and 'body' fields only."},
                {"role": "user", "content": f"Draft an email to {to}. Context: {context}. Subject hint: {subject_hint}"}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        text = response.choices[0].message.content.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.strip()
        
        return json.loads(text)
    except Exception as e:
        return {"subject": subject_hint, "body": context, "error": str(e)}

async def transcribe_audio(audio_data: bytes) -> str:
    # Groq supports Whisper!
    try:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=("audio.webm", audio_data)
        )
        return transcription.text
    except Exception as e:
        return f"Error transcribing audio: {str(e)}"
