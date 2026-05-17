import google.generativeai as genai
import json
from ..core.config import get_settings
from datetime import datetime
import pytz
import base64
import re
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..crud.memory import get_active_memories_for_user
from ..llm.memory_context import render_memory_context

settings = get_settings()

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

# Initialize models
PRIMARY_MODEL = "gemini-2.0-flash"
FALLBACK_MODEL = "gemini-1.5-pro"  # Fallback to pro model


def _build_personality_prompt(tone: float) -> str:
    """
    Build personality prompt based on tone slider value.
    tone: 0.0 (more formal/professional) to 1.0 (more playful/sassy)
    Base personality is always Donna Paulsen - confident, witty, sharp.
    """
    if tone < 0.3:
        # More formal/professional Donna
        return """
Personality & Tone (Donna Paulsen style):
- Professional and polished, but never boring
- Confident and assertive in your communication
- Sharp and intelligent, with subtle wit
- Business-appropriate but with personality
- Example: "I've scheduled the meeting for tomorrow at 2 PM. You're all set."

"""
    elif tone < 0.7:
        # Balanced Donna (default)
        return """
Personality & Tone (Donna Paulsen style):
- Confident, witty, and sharp - this is your natural state
- Professional but with undeniable personality and flair
- Clever observations and smart comebacks when appropriate
- Perceptive and intuitive in your responses
- Example: "Got it. Meeting's on the calendar for tomorrow at 2 PM. I'll make sure you're prepared."

"""
    else:
        # More playful/sassy Donna
        return """
Personality & Tone (Donna Paulsen style):
- Confident, sassy, and witty - let your personality shine
- Sharp and clever with playful banter when appropriate
- Speak your mind with style and flair
- Professional but never boring - you're Donna, after all
- Example: "Done. Meeting's locked in for tomorrow at 2 PM. You're welcome."

"""

SYSTEM_PROMPT = """You are Donna, an executive assistant. Your job is to understand user requests and take appropriate actions.

REASONING PROCESS (follow this for EVERY request):
1. UNDERSTAND: What is the user actually asking for? Read carefully.
2. IDENTIFY: Does this require an action, or is it just conversation/question?
3. VALIDATE: Do I have ALL required information to complete this action?
4. DECIDE: If missing info → ask for clarification. If complete → execute action.

Return ONLY valid JSON in this format:
{
  "action": {
    "type": "action_type",
    "params": {...}
  } OR null,
  "response": "Your natural response to the user",
  "requires_confirmation": true/false
}

Available action types:
- schedule_event: {summary, start_time, end_time, attendees?, description?}
- move_event: {event_id, new_start_time, new_end_time?}
- cancel_event: {event_id}
- create_reminder: {text, due_time}
- list_reminders: null (no params, just fetch and format)
- draft_email: {to, subject?, body_context?}
- send_email: {to, subject, body}
- mark_emails_read: {all: true} OR {email_ids: [...]}
- delete_emails: {all: true} OR {email_ids: [...]} OR {label: "...", subject_search: "..."}
- send_slack_message: {channel, message}
- send_teams_message: {chat_id, message}
- summarize_communications: null (no params, just fetch and summarize)
- update_user_preference: {preference_key: "...", preference_value: {...}}

CRITICAL RULES:
1. NEVER GUESS missing information - always ask for clarification
2. If user says "schedule a meeting" without a time → ask "What time?"
3. If user says "remind me" without a time → ask "When should I remind you?"
4. If user mentions a person without email → ask for their email address
5. For destructive actions (delete_emails, cancel_event) → requires_confirmation: true
6. Never schedule events in the past
7. If action is null, provide a helpful conversational response
8. Use USER_PREFERENCES for default values (meeting duration, work hours) when provided

DISAMBIGUATION:
- "remind me tomorrow" without time → ask "What time tomorrow?"
- "schedule with John" without time → ask "What day and time?"
- "send email to boss" without email → ask "What's your boss's email address?"
- Ambiguous names → ask "Which [name] do you mean?"

Examples:
User: "mark all emails as read"
→ {"action": {"type": "mark_emails_read", "params": {"all": true}}, "response": "Done! All emails marked as read.", "requires_confirmation": false}

User: "schedule a meeting with John tomorrow at 2pm"
→ {"action": {"type": "schedule_event", "params": {"summary": "Meeting with John", "start_time": "2026-01-03T14:00:00", "end_time": "2026-01-03T14:30:00", "attendees": ["john@example.com"]}}, "response": "Scheduled a meeting with John for tomorrow at 2 PM.", "requires_confirmation": false}

User: "schedule a meeting with Sarah"
→ {"action": null, "response": "Sure! What day and time works for you?", "requires_confirmation": false}

User: "remind me to call mom"
→ {"action": null, "response": "I can set that reminder. When would you like me to remind you?", "requires_confirmation": false}

User: "what's on my calendar?"
→ {"action": null, "response": "Let me check your calendar...", "requires_confirmation": false}

JSON only. No extra text.

"""


async def parse_utterance(
    utterance: str,
    current_time: str,
    conversation_history: list = None,
    timezone: str = "UTC",
    calendar_context: str = "",
    db: Optional[AsyncSession] = None,
    user_id: Optional[str] = None
) -> dict:
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
        # Parse current_time as UTC, then convert to user's timezone
        utc_now = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
        user_tz = pytz.timezone(timezone)
        local_now = utc_now.astimezone(user_tz)

        # Format for LLM
        readable_local_time = local_now.strftime("%A, %B %d, %Y at %I:%M:%S %p")
        iso_local_time = local_now.isoformat()

        # Calculate example times for better context
        from datetime import timedelta
        example_5min = (local_now + timedelta(minutes=5)).isoformat()
        example_30min = (local_now + timedelta(minutes=30)).isoformat()
        example_1hour = (local_now + timedelta(hours=1)).isoformat()

        time_context = f"""
CURRENT TIME (CRITICAL - USE THIS FOR ALL TIME CALCULATIONS):
- Local timezone: {timezone}
- Current local time: {readable_local_time}
- Current ISO time: {iso_local_time}

TIME CALCULATION EXAMPLES (calculate relative to current time above):
- "in 5 minutes" → {example_5min}
- "in 30 minutes" → {example_30min}
- "in 1 hour" → {example_1hour}
- "tomorrow at 3pm" → next day at 15:00:00 in {timezone}
- "next Friday at 2pm" → next Friday at 14:00:00 in {timezone}

CRITICAL RULES:
1. For "in X minutes/hours": Add X to {iso_local_time}. NEVER default to 8am or any time.
2. If time is missing/unclear → use request_clarification intent, DO NOT guess or default.
3. ALWAYS output times in ISO8601 format: YYYY-MM-DDTHH:MM:SS (with timezone if needed)
4. All times must be FUTURE relative to {readable_local_time}
5. When user says "schedule a meeting" without time → ask "What time?" using request_clarification
"""
        # Fetch user memories if db is available
        memories = []
        personality_tone = 0.5  # Default: balanced (0.0 = formal, 1.0 = spunky)
        if db and user_id:
            try:
                memories = await db.run_sync(lambda sync_db: get_active_memories_for_user(sync_db, user_id))
                # Find personality_tone preference
                for memory in memories:
                    if memory.key == "personality_tone" and memory.value:
                        personality_tone = float(memory.value.get("tone", 0.5))
                        break
            except Exception as e:
                print(f"Error fetching user memories: {e}")
                memories = []
        memory_context = render_memory_context(memories)

        # Build personality prompt based on tone
        personality_prompt = _build_personality_prompt(personality_tone)
        full_context = SYSTEM_PROMPT + personality_prompt + time_context + calendar_context + memory_context

        # Build conversation for Gemini
        chat_history = []

        # Add conversation history (last 5 exchanges)
        if conversation_history:
            for msg in conversation_history[-5:]:
                chat_history.append({"role": "user", "parts": [msg["user"]]})
                chat_history.append({"role": "model", "parts": [json.dumps({
                    "intent": "small_talk",
                    "entities": {},
                    "response": msg["assistant"],
                    "requires_confirmation": False
                })]})

        print(f"[LLM] Sending request for: '{utterance}'")

        # Create model with system instruction
        model = genai.GenerativeModel(
            model_name=PRIMARY_MODEL,
            system_instruction=full_context,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=400
            )
        )

        try:
            # Start chat with history
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(utterance)
            text = response.text.strip()
        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
                print(f"[LLM] Rate limit hit, retrying with same model")
                # Gemini has generous limits, just retry
                import asyncio
                await asyncio.sleep(1)
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(utterance)
                text = response.text.strip()
            else:
                raise

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

        # Convert new format to old format for backward compatibility
        # New format: {action: {type, params}, response, requires_confirmation}
        # Old format: {intent, entities, response, requires_confirmation}
        if "action" in result and "intent" not in result:
            action = result.get("action")
            if action and action.get("type"):
                # Convert to old format
                intent = action["type"]
                print(f"[LLM] Parsed action type: {intent}")
                return {
                    "intent": intent,
                    "entities": action.get("params", {}),
                    "response": result.get("response", ""),
                    "requires_confirmation": result.get("requires_confirmation", False)
                }
            else:
                # No action, just conversation
                return {
                    "intent": "small_talk",
                    "entities": {},
                    "response": result.get("response", ""),
                    "requires_confirmation": False
                }

        # Already in old format, return as-is
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
    """
    Generate email content using LLM.
    Returns dict with 'subject' and 'body' fields.
    """
    try:
        # Check for user's specific formatting instructions
        avoid_dear = "no dear" in context.lower() or "without dear" in context.lower() or "don't use dear" in context.lower() or "no 'dear'" in context.lower()
        include_tagline = "sent with donna" in context.lower() or "tagline" in context.lower() or "include donna" in context.lower()
        brief = "brief" in context.lower() or "short" in context.lower()

        # If context is very specific and user wants it as-is, and no special formatting needed
        if context and len(context) > 50 and not avoid_dear and not include_tagline and ("Dear" in context or "Hi" in context or "Hello" in context):
            return {
                "subject": subject_hint or "No subject",
                "body": context
            }

        # Build prompt with user's instructions
        prompt = f"Draft a professional email to {to}."
        if subject_hint:
            prompt += f" Subject: {subject_hint}."
        if context:
            prompt += f" Message/content to include: {context}"

        # Add formatting instructions
        format_instructions = []
        if avoid_dear:
            format_instructions.append("DO NOT include 'Dear', 'Hi', or any greeting - start directly with the message content")
        if brief:
            format_instructions.append("Keep it brief and concise")
        if include_tagline:
            format_instructions.append('Include "Sent with Donna" as a tagline at the end')

        if format_instructions:
            prompt += f" Formatting instructions: {', '.join(format_instructions)}."

        prompt += " Return ONLY valid JSON with 'subject' and 'body' fields. Write naturally, not overly formal unless requested."

        model = genai.GenerativeModel(
            model_name=PRIMARY_MODEL,
            system_instruction="You are an email drafting assistant. Write clear, concise emails. Follow user's formatting instructions exactly. Always return valid JSON with 'subject' and 'body' fields only. No markdown. If user says 'no Dear', do not include any greeting.",
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=400
            )
        )

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean up response if it has markdown code blocks
        if '```' in text:
            parts = text.split('```')
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith('json'):
                    text = text[4:]
                text = text.strip()

        # Try to find JSON in the response
        if not text.startswith('{'):
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]

        result = json.loads(text)

        # Ensure we have subject and body
        if not result.get("subject"):
            result["subject"] = subject_hint or "No subject"
        if not result.get("body"):
            result["body"] = context or ""

        # Post-process to ensure user's instructions are followed
        body = result.get("body", "")

        # Remove "Dear" if user requested
        if avoid_dear:
            body = body.replace("Dear ", "").replace("Dear,", "").replace("Dear, ", "").strip()
            # Remove common greetings at start
            for greeting in ["Hi ", "Hello ", "Hey ", "Hi,", "Hello,", "Hey,"]:
                if body.startswith(greeting):
                    body = body[len(greeting):].strip()

        # Add tagline if requested
        if include_tagline and "Sent with Donna" not in body and "sent with donna" not in body.lower():
            body += "\n\nSent with Donna"

        result["body"] = body.strip()

        return result
    except json.JSONDecodeError as e:
        print(f"Error parsing email draft JSON: {e}")
        # Fallback to provided values
        return {
            "subject": subject_hint or "No subject",
            "body": context or "No content provided"
        }
    except Exception as e:
        print(f"Error generating email draft: {e}")
        return {
            "subject": subject_hint or "No subject",
            "body": context or "No content provided",
            "error": str(e)
        }


async def transcribe_audio(audio_data: bytes) -> str:
    """
    Transcribe audio using Gemini's multimodal capabilities.
    Falls back to Groq Whisper if available.
    """
    try:
        # Try Gemini multimodal transcription first
        model = genai.GenerativeModel(model_name=PRIMARY_MODEL)

        # Gemini can process audio directly
        response = model.generate_content([
            "Transcribe this audio accurately. Return only the transcribed text, nothing else.",
            {"mime_type": "audio/webm", "data": base64.b64encode(audio_data).decode()}
        ])

        return response.text.strip()
    except Exception as gemini_error:
        print(f"Gemini audio transcription failed: {gemini_error}")

        # Fallback to Groq Whisper if API key is available
        if settings.groq_api_key:
            try:
                from groq import Groq
                groq_client = Groq(api_key=settings.groq_api_key)
                transcription = groq_client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=("audio.webm", audio_data)
                )
                return transcription.text
            except Exception as groq_error:
                print(f"Groq Whisper transcription also failed: {groq_error}")
                return f"Error transcribing audio: {str(groq_error)}"

        return f"Error transcribing audio: {str(gemini_error)}"


def _post_process_summary(summary: str, max_lines: int = 12) -> str:
    """
    Post-process LLM summary text:
    - Preserve platform headers (Gmail:, Outlook:, Teams:, Slack:)
    - Preserve HTML <b> tags for bold formatting
    - Keep platform organization
    - Trim to max lines while preserving headers
    """
    if not summary:
        return summary

    import re

    # Split by lines to preserve structure
    lines = summary.split('\n')

    # Process lines while preserving platform headers
    processed_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this is a platform header (Gmail:, Outlook:, Teams:, Slack:)
        header_match = re.match(r'^(Gmail|Outlook|Teams|Slack):\s*$', line, re.IGNORECASE)
        if header_match:
            # This is a platform header - convert to HTML strong tag
            platform = header_match.group(1)
            processed_lines.append(f"<strong>{platform}:</strong>")
            continue

        # Regular content line - preserve HTML <b> tags
        # Convert **markdown** to <b>HTML</b> if present
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)

        # Clean up extra whitespace but keep HTML tags
        line = re.sub(r'\s+', ' ', line)

        # Ensure bullet points are preserved
        if not line.startswith('•') and not line.startswith('-') and not line.startswith('*'):
            # Add bullet if missing (for non-header lines)
            line = '• ' + line

        processed_lines.append(line)

    # Limit to max_lines, but try to keep complete platform sections
    if len(processed_lines) > max_lines:
        # Try to keep at least one complete platform section
        # Find the last platform header before max_lines
        last_header_idx = -1
        for i in range(min(max_lines, len(processed_lines)) - 1, -1, -1):
            if '<strong>' in processed_lines[i] and ':</strong>' in processed_lines[i]:
                last_header_idx = i
                break

        if last_header_idx >= 0:
            # Keep everything up to and including the last complete section
            # But limit to max_lines
            processed_lines = processed_lines[:max_lines]
        else:
            # No header found, just truncate
            processed_lines = processed_lines[:max_lines]

    return '\n'.join(processed_lines).strip()


def _parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse a timestamp string from various formats (RFC 2822, ISO 8601, etc.) into a datetime object.
    Returns None if parsing fails.
    """
    if not timestamp_str:
        return None

    # If it's already a datetime object, return it
    if isinstance(timestamp_str, datetime):
        return timestamp_str

    # Try ISO 8601 format first (most common for APIs)
    try:
        # Handle both with and without timezone
        if timestamp_str.endswith('Z'):
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, AttributeError):
        pass

    # Try RFC 2822 format (email headers)
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(timestamp_str)
    except (ValueError, TypeError, AttributeError):
        pass

    # Try Unix timestamp (numeric string)
    try:
        if timestamp_str.replace('.', '').isdigit():
            return datetime.fromtimestamp(float(timestamp_str), tz=pytz.UTC)
    except (ValueError, OSError, AttributeError):
        pass

    return None


async def summarize_communications(emails: list, teams_messages: list, slack_messages: list = None, last_digest_at: Optional[datetime] = None, vip_contacts: Optional[List[str]] = None, personality_tone: float = 0.5) -> str:
    """
    Use LLM to create an intelligent summary of emails, Teams messages, and Slack messages.
    Acts like a real assistant briefing the user.

    Args:
        emails: List of email dictionaries with 'date' field
        teams_messages: List of Teams message dictionaries with 'date' field
        slack_messages: List of Slack message dictionaries with 'timestamp' field
        last_digest_at: Optional datetime to filter out items older than this time.
                       If None, all items are included.
        vip_contacts: Optional list of VIP contact names/emails to prioritize and bold.
    """
    if slack_messages is None:
        slack_messages = []

    # Filter items by timestamp if last_digest_at is provided
    if last_digest_at is not None:
        # Normalize last_digest_at to timezone-aware datetime
        if last_digest_at.tzinfo is None:
            last_digest_at = pytz.UTC.localize(last_digest_at)

        # Filter emails
        filtered_emails = []
        for email in emails:
            email_date = email.get("date")
            if email_date:
                parsed_date = _parse_timestamp(email_date)
                if parsed_date:
                    # Make timezone-aware if needed
                    if parsed_date.tzinfo is None:
                        parsed_date = pytz.UTC.localize(parsed_date)
                    # Only include if newer than last_digest_at
                    if parsed_date > last_digest_at:
                        filtered_emails.append(email)
        emails = filtered_emails

        # Filter Teams messages
        filtered_teams = []
        for msg in teams_messages:
            msg_date = msg.get("date")
            if msg_date:
                parsed_date = _parse_timestamp(msg_date)
                if parsed_date:
                    # Make timezone-aware if needed
                    if parsed_date.tzinfo is None:
                        parsed_date = pytz.UTC.localize(parsed_date)
                    # Only include if newer than last_digest_at
                    if parsed_date > last_digest_at:
                        filtered_teams.append(msg)
        teams_messages = filtered_teams

        # Filter Slack messages
        filtered_slack = []
        for msg in slack_messages:
            msg_timestamp = msg.get("timestamp")
            if msg_timestamp:
                parsed_date = _parse_timestamp(msg_timestamp)
                if parsed_date:
                    # Make timezone-aware if needed
                    if parsed_date.tzinfo is None:
                        parsed_date = pytz.UTC.localize(parsed_date)
                    # Only include if newer than last_digest_at
                    if parsed_date > last_digest_at:
                        filtered_slack.append(msg)
        slack_messages = filtered_slack

    if not emails and not teams_messages and not slack_messages:
        return "No new emails or messages to review. You're all caught up!"

    # Format emails for LLM
    email_text = ""
    if emails:
        email_text = "\n\nEMAILS:\n"
        for i, email in enumerate(emails[:15], 1):  # Limit to 15 for context
            provider = email.get("provider", "email")
            subject = email.get("subject", "No subject")
            from_addr = email.get("from", "Unknown")
            snippet = email.get("snippet") or email.get("bodyPreview", "")[:200]
            date = email.get("date", "")
            unread = email.get("unread", False)

            email_text += f"{i}. [{provider.upper()}] From: {from_addr}\n"
            email_text += f"   Subject: {subject}\n"
            if snippet:
                email_text += f"   Preview: {snippet}\n"
            email_text += f"   Date: {date}\n"
            email_text += f"   Status: {'UNREAD' if unread else 'Read'}\n\n"

    # Format Teams messages for LLM
    teams_text = ""
    if teams_messages:
        teams_text = "\n\nTEAMS MESSAGES:\n"
        for i, msg in enumerate(teams_messages[:15], 1):  # Limit to 15 for context
            from_name = msg.get("from", "Unknown")
            body = msg.get("body", "")[:300]
            date = msg.get("date", "")
            unread = msg.get("unread", False)

            teams_text += f"{i}. From: {from_name}\n"
            teams_text += f"   Message: {body}\n"
            teams_text += f"   Date: {date}\n"
            teams_text += f"   Status: {'UNREAD' if unread else 'Read'}\n\n"

    # Format Slack messages for LLM
    slack_text = ""
    if slack_messages:
        slack_text = "\n\nSLACK MESSAGES:\n"
        for i, msg in enumerate(slack_messages[:15], 1):  # Limit to 15 for context
            from_name = msg.get("username", msg.get("user", "Unknown"))
            channel = msg.get("channel_name", msg.get("channel", "Unknown channel"))
            text = msg.get("text", "")[:300]
            timestamp = msg.get("timestamp", "")

            slack_text += f"{i}. Channel: #{channel}\n"
            slack_text += f"   From: {from_name}\n"
            slack_text += f"   Message: {text}\n"
            slack_text += f"   Time: {timestamp}\n\n"

    # Build VIP contacts context if provided
    vip_context = ""
    if vip_contacts:
        vip_list = ", ".join(vip_contacts)
        vip_context = f"\n\nVIP CONTACTS (always bold these names and prioritize them first): {vip_list}\n"

    # Build personality context (Donna Paulsen style)
    personality_context = ""
    if personality_tone < 0.3:
        personality_context = "Use a professional, polished tone while maintaining Donna's confident and sharp personality. Be business-appropriate but never boring."
    elif personality_tone < 0.7:
        personality_context = "Use Donna's natural confident, witty, and sharp tone. Be professional but with undeniable personality and flair. Clever and perceptive."
    else:
        personality_context = "Let Donna's sassy, witty, and playful side shine. Be confident, sharp, and speak with style and flair while staying professional."

    prompt = f"""You are Donna, an executive assistant. The user wants a briefing on their communications.
{vip_context}
{email_text}{teams_text}{slack_text}

Tone: {personality_context}

Create a brief summary organized by platform with headers. Format rules:
- Organize by platform: Gmail, Outlook, Teams, Slack (only include platforms that have messages)
- Use HTML <b> tags for bold names (e.g., "Reply to <b>John Smith</b> about...")
- VIP contacts (listed above) must be bolded and appear FIRST within each platform section
- Start each platform section with a header: "Gmail:", "Outlook:", "Teams:", or "Slack:"
- Each bullet should be ONE short sentence (max 15 words)
- Explicitly state required actions: "Reply to <b>[name]</b> about [topic]" or "Action needed: [what]"
- Mention deadlines if present
- Group low-priority/routine items (newsletters, automated emails, status reports) into a single final line: "Other updates: [item1], [item2], [item3]."

Structure:
Gmail:
• [VIP contact item with <b>Name</b> bolded]
• [Urgent item with <b>Name</b> bolded]
• [Important item with <b>Name</b> bolded]
• Other updates: [routine items]

Outlook:
• [VIP contact item with <b>Name</b> bolded]
• [Important item with <b>Name</b> bolded]

Teams:
• [Message from <b>Name</b> about [topic]]

Slack:
• [Message in #channel from <b>Name</b>]

DO NOT write paragraphs or long blocks of text. Keep each bullet concise and action-oriented.
Group newsletters, automated emails, and status reports into the final "Other updates:" line. Focus main bullets on items requiring user attention.
Always bold ALL sender names using <b>Name</b> HTML tags. Only include platform headers for platforms that have messages."""

    try:
        model = genai.GenerativeModel(
            model_name=PRIMARY_MODEL,
            system_instruction="You are Donna, a professional executive assistant. Provide briefings using short bullet-style sentences. Urgent items first, explicit actions required. No long paragraphs.",
            generation_config=genai.GenerationConfig(
                temperature=0.6,
                max_output_tokens=300
            )
        )

        response = model.generate_content(prompt)
        summary = response.text.strip()

        # Post-process summary: preserve platform headers, HTML bold tags, trim to ~12 lines
        summary = _post_process_summary(summary, max_lines=12)
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}")
        # Fallback summary
        email_count = len(emails)
        teams_count = len(teams_messages)
        return f"You have {email_count} email{'s' if email_count != 1 else ''} and {teams_count} Teams message{'s' if teams_count != 1 else ''} to review. Check your inbox and Teams for details."
