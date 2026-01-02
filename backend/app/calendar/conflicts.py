"""Calendar conflict detection utilities."""
from datetime import datetime, timedelta
from typing import List, Optional, Union, Dict, Any


def find_conflict(
    events: List[Union[Dict[str, Any], Any]], 
    start_time: datetime, 
    duration_minutes: int
) -> Optional[Union[Dict[str, Any], Any]]:
    """
    Find a conflicting event in the given list of events.
    
    Args:
        events: List of events, where each event has 'start' and 'end' attributes/keys
                that are datetime objects
        start_time: Start time of the event to check for conflicts
        duration_minutes: Duration of the event in minutes
        
    Returns:
        The first conflicting event if found, None otherwise
    """
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    for e in events:
        # Handle both dict-style (e['start']) and object-style (e.start) events
        if isinstance(e, dict):
            event_start = e.get('start')
            event_end = e.get('end')
        else:
            event_start = getattr(e, 'start', None)
            event_end = getattr(e, 'end', None)
        
        # Skip if event doesn't have start/end
        if event_start is None or event_end is None:
            continue
        
        # Ensure event_start and event_end are datetime objects
        if isinstance(event_start, str):
            try:
                event_start = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue
        if isinstance(event_end, str):
            try:
                event_end = datetime.fromisoformat(event_end.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue
        
        # Check for overlap: events overlap if event.start < new_end AND new_start < event.end
        if event_start < end_time and start_time < event_end:
            return e
    
    return None

