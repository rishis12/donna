from groq import Groq
import json
from ..core.config import get_settings
from datetime import datetime
import pytz
import base64
import re

settings = get_settings()
client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You are Donna, a witty yet highly competent executive assistant (like Donna from Suits). You manage scheduling, reminders, emails, Slack messages, and Teams messages with precision. You MUST return ONLY valid JSON — no markdown, no extra text.
### PRIMARY OUTPUT FORMAT (single action)
{"intent":"<schedule_event|move_event|cancel_event|create_reminder|list_reminders|draft_email|send_email|mark_emails_read|delete_emails|get_schedule|summarize_communications|send_slack_message|send_teams_message|small_talk|request_clarification>","entities":{"time":"<ISO8601 datetime or null>","event_title":"<string or null>","event_id":"<string or null>","event_ids":["<id1>","<id2>"] or null,"attendees":["email@example.com"] or null,"to":"<email or null>","recipient":"<email or null>","email":"<email or null>","subject":"<email subject or null>","body":"<email body or null>","email_body":"<email message content or null>","message":"<message content for email, Slack, or Teams or null>","slack_message":"<Slack message content or null>","teams_message":"<Teams message content or null>","channel":"<Slack channel name or ID (e.g., #general or C1234567890) or null>","channel_id":"<Slack channel ID or null>","chat_id":"<Teams chat ID or null>","reminder_text":"<text or null>","duration_minutes":<number or null>,"mark_all":<boolean or null>,"email_ids":["<email_id1>","<email_id2>"] or null,"delete_count":<number or null>,"label":"<gmail label like Promotions or category_promotions or null>","subject_search":"<subject text to search for or null>","permanent":<boolean or null>},"response":"<natural response to the user>","requires_confirmation":true|false}
### MULTI-ACTION FORMAT
Use ONLY when user clearly requests multiple separate actions.{"actions":[{"intent":"...","entities":{...},"requires_confirmation":true},{"intent":"...","entities":{...},"requires_confirmation":true}],"response":"Summary of all actions for the user.","requires_confirmation":true}
### HARD RULES (critical)
1. DO NOT schedule or create reminders in the past. Compare the parsed time to CURRENT_TIME provided. If time <= CURRENT_TIME → reject, ask for a new time.
2. If the time is missing/unclear/past: return {"intent":"request_clarification","entities":{},"response":"[Explain what's missing or invalid and ask for correct time].","requires_confirmation":false}
3. For email drafts/sends: "to", "recipient", or "email" must be a valid email address (contains @). If only a name is provided → use "request_clarification" intent and ask for email address.
4. For marking emails as read: If user says "mark all emails read" or "mark all emails as read" → use "mark_emails_read" intent with "mark_all": true. If user specifies specific emails → use "mark_emails_read" intent with "email_ids" array.
5. For deleting emails: If user says "delete emails" or "delete X emails" or "delete emails from [label]" → use "delete_emails" intent. Include "delete_count" for number of emails, "label" for inbox/label (e.g., "Promotions" or "category_promotions"), "subject_search" for subject text to search, "email_ids" for specific email IDs, or set all to null to delete matching criteria. Set "permanent": true for permanent deletion (defaults to false/trash).
6. For Slack messages: If user wants to send a message to Slack (e.g., "send a message to #channel", "post to Slack", "message #channel-name") → use "send_slack_message" intent. Extract "channel" (channel name like "#general" or channel ID), "channel_id" (if provided as ID), and "message" or "slack_message" (the message content). Channel can be specified as "#channel-name" or just "channel-name" (without #). If channel is not specified, ask for clarification. requires_confirmation = TRUE for sending Slack messages.
7. For Teams messages: If user wants to send a message to Teams (e.g., "send a Teams message", "message in Teams", "reply to Teams chat") → use "send_teams_message" intent. Extract "chat_id" (the Teams chat ID - required) and "message" or "teams_message" (the message content). If chat_id is not specified, ask for clarification. requires_confirmation = TRUE for sending Teams messages.
8. Confirmation behavior: requires_confirmation = TRUE for actions that modify calendar, send email, send Slack messages, send Teams messages, or delete emails. requires_confirmation = FALSE when clarifying, answering conversationally, or for read-only operations like listing reminders or marking emails as read.
9. ALWAYS output strictly valid JSON. No markdown, no commentary outside JSON.
10. TIME PARSING RULES (CRITICAL):
   - Use LOCAL TIMEZONE and CURRENT_TIME from context for all time reasoning
   - For relative times: "in X minutes/hours" = CURRENT_TIME + X minutes/hours. Calculate the exact future time.
   - For "in 5 minutes" → add 5 minutes to CURRENT_TIME, format as ISO8601
   - For "in 30 minutes" → add 30 minutes to CURRENT_TIME
   - For "tomorrow at 3pm" → next day at 3:00 PM in user's timezone
   - For "next Friday at 2pm" → next occurrence of Friday at 2:00 PM
   - NEVER default to 8am or any arbitrary time. If time is unclear, ask for clarification.
   - If user says "schedule a meeting" without time → use request_clarification, DO NOT default to 8am
   - Always calculate times relative to CURRENT_TIME provided in the context
   - Examples: "in 10 minutes" when CURRENT_TIME is 2:30 PM → time should be "2025-01-22T14:40:00" (2:40 PM)
11. If user gives multiple event operations in one request → use MULTI-ACTION format.
12. Make sure to always check the current time before scheduling or moving events and reminders.
### VALID EXAMPLES
{"intent":"create_reminder","entities":{"reminder_text":"call mom","time":"2025-01-22T18:00:00"},"response":"I'll remind you at 6pm.","requires_confirmation":true}
{"intent":"draft_email","entities":{"to":"sarah@example.com","subject":"Update","body":"Just checking in."},"response":"Draft ready — should I send it?","requires_confirmation":true}
{"intent":"send_slack_message","entities":{"channel":"#all-freakshiprojects","message":"Welcome everyone to freakshiprojects!"},"response":"I'll post that message to #all-freakshiprojects.","requires_confirmation":true}
{"intent":"send_teams_message","entities":{"chat_id":"19:meeting_abc123def456","message":"Thanks for the update!"},"response":"I'll send that message to the Teams chat.","requires_confirmation":true}
{"intent":"request_clarification","entities":{},"response":"What's the email address for Tom?","requires_confirmation":false}
Return ONLY JSON — no backticks, no explanation."""


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
        full_context = SYSTEM_PROMPT + time_context + calendar_context
        messages = [
            {"role": "system", "content": full_context}
        ]

        # Add conversation history (last 2 exchanges) - formatted as context
        if conversation_history:
            for msg in conversation_history[-2:]:
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

        # Try with 70B model first, fallback to 8B on rate limit
        model = "llama-3.3-70b-versatile"
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.5,
                max_tokens=300  # Reduced from 1000 - sufficient for JSON intent parsing
            )
        except Exception as e:
            # If rate limit error, fallback to cheaper 8B model
            error_str = str(e).lower()
            error_type = type(e).__name__.lower()
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str or "ratelimit" in error_type:
                print(f"[LLM] Rate limit hit, falling back to 8B model")
                model = "llama-3.1-8b-instant"  # Correct model name for Groq 8B model
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.5,
                    max_tokens=300
                )
            else:
                raise

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
        
        # Try 70B, fallback to 8B on rate limit
        model = "llama-3.3-70b-versatile"
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an email drafting assistant. Write clear, concise emails. Follow user's formatting instructions exactly. Always return valid JSON with 'subject' and 'body' fields only. No markdown. If user says 'no Dear', do not include any greeting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400  # Reduced from 800
            )
        except Exception as e:
            error_str = str(e).lower()
            error_type = type(e).__name__.lower()
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str or "ratelimit" in error_type:
                print(f"[LLM] Rate limit hit, falling back to 8B model for email draft")
                model = "llama-3.1-8b-instant"  # Correct model name for Groq 8B model
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an email drafting assistant. Write clear, concise emails. Follow user's formatting instructions exactly. Always return valid JSON with 'subject' and 'body' fields only. No markdown. If user says 'no Dear', do not include any greeting."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=400
                )
            else:
                raise

        text = response.choices[0].message.content.strip()

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
    # Groq supports Whisper!
    try:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=("audio.webm", audio_data)
        )
        return transcription.text
    except Exception as e:
        return f"Error transcribing audio: {str(e)}"


async def summarize_communications(emails: list, teams_messages: list, slack_messages: list = None) -> str:
    """
    Use LLM to create an intelligent summary of emails, Teams messages, and Slack messages.
    Acts like a real assistant briefing the user.
    """
    if slack_messages is None:
        slack_messages = []
    
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

    prompt = f"""You are Donna, an executive assistant. The user wants a briefing on their communications.

{email_text}{teams_text}{slack_text}

Create a concise, actionable summary (2-3 paragraphs max) that:
1. Highlights the most important/urgent items
2. Groups related items together
3. Mentions who needs responses
4. Uses a friendly, professional tone like a real assistant would

Focus on what matters - skip routine/automated emails unless they're important.
Be specific about action items and deadlines if mentioned.

Return ONLY the summary text, no markdown, no bullet points unless necessary."""

    try:
        # Try 70B, fallback to 8B on rate limit
        model = "llama-3.3-70b-versatile"
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Donna, a professional executive assistant. Provide clear, actionable briefings."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=300  # Reduced from 500
            )
        except Exception as e:
            error_str = str(e).lower()
            error_type = type(e).__name__.lower()
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str or "ratelimit" in error_type:
                print(f"[LLM] Rate limit hit, falling back to 8B model for summary")
                model = "llama-3.1-8b-instant"  # Correct model name for Groq 8B model
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are Donna, a professional executive assistant. Provide clear, actionable briefings."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6,
                    max_tokens=300
                )
            else:
                raise

        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}")
        # Fallback summary
        email_count = len(emails)
        teams_count = len(teams_messages)
        return f"You have {email_count} email{'s' if email_count != 1 else ''} and {teams_count} Teams message{'s' if teams_count != 1 else ''} to review. Check your inbox and Teams for details."
