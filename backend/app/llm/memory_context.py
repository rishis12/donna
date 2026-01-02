def render_memory_context(memories):
    if not memories:
        return ""

    lines = ["USER_PREFERENCES:"]
    for m in memories:
        if m.key == "default_meeting_duration":
            lines.append(f"- Default meeting duration: {m.value.get('minutes')} minutes.")
        elif m.key == "work_hours":
            lines.append(f"- Work hours: {m.value.get('start')}–{m.value.get('end')} ({m.value.get('timezone')}).")
        else:
            lines.append(f"- {m.key}: {m.value}")
    return "\n".join(lines) + "\n"

