import { useState, useEffect } from 'react'
import { Calendar, Clock, Users, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'

interface CalendarEvent {
  id: string
  summary: string
  start: string
  end: string
  attendees?: string[]
  description?: string
}

export default function SchedulePanel() {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchEvents = async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch more events to show a week ahead
      const response = await api.get('/calendar/events?max_results=50')
      setEvents(response.events || [])
    } catch (err: any) {
      if (err.message?.includes('not connected')) {
        setError('Connect your Google Calendar in Settings to see your schedule.')
      } else {
        setError('Failed to load calendar events')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEvents()
  }, [])

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  }

  const isToday = (dateStr: string) => {
    const eventDate = new Date(dateStr).toDateString()
    return eventDate === new Date().toDateString()
  }

  const isTomorrow = (dateStr: string) => {
    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    const eventDate = new Date(dateStr).toDateString()
    return eventDate === tomorrow.toDateString()
  }

  const getRelativeDay = (dateStr: string) => {
    if (isToday(dateStr)) return 'Today'
    if (isTomorrow(dateStr)) return 'Tomorrow'
    return formatDate(dateStr)
  }

  // Group events by day
  const groupedEvents = events.reduce((acc, event) => {
    const day = new Date(event.start).toDateString()
    if (!acc[day]) acc[day] = []
    acc[day].push(event)
    return acc
  }, {} as Record<string, CalendarEvent[]>)

  const sortedDays = Object.keys(groupedEvents).sort((a, b) => 
    new Date(a).getTime() - new Date(b).getTime()
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 text-primary-400 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center px-4">
        <div className="w-14 h-14 rounded-2xl bg-surface-100 flex items-center justify-center mb-4">
          <Calendar className="w-7 h-7 text-surface-400" />
        </div>
        <p className="text-surface-500 text-sm">{error}</p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-surface-800 font-semibold flex items-center gap-2">
          <Calendar className="w-4 h-4 text-primary-400" />
          Your Schedule
        </h2>
        <button
          onClick={fetchEvents}
          className="p-2 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-xl transition-all"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <div className="w-12 h-12 rounded-2xl bg-surface-100 flex items-center justify-center mb-3">
              <Calendar className="w-6 h-6 text-surface-400" />
            </div>
            <p className="text-surface-600 text-sm font-medium">No upcoming events</p>
            <p className="text-surface-400 text-xs mt-1">Ask Donna to schedule something!</p>
          </div>
        ) : (
          sortedDays.map(day => (
            <div key={day}>
              {/* Day Header */}
              <div className="sticky top-0 bg-white/95 backdrop-blur-sm py-2 z-10">
                <span className={`text-xs font-medium px-3 py-1.5 rounded-full ${
                  isToday(groupedEvents[day][0].start) 
                    ? 'bg-primary-50 text-primary-500' 
                    : 'bg-surface-100 text-surface-500'
                }`}>
                  {getRelativeDay(groupedEvents[day][0].start)}
                </span>
              </div>

              {/* Events for this day */}
              <div className="space-y-2 mt-2">
                {groupedEvents[day].map(event => (
                  <div
                    key={event.id}
                    className="group bg-surface-50 hover:bg-surface-100 border border-surface-200 rounded-2xl p-4 transition-all cursor-pointer"
                  >
                    <div className="flex items-start gap-3">
                      {/* Time */}
                      <div className="flex flex-col items-center min-w-[50px]">
                        <span className="text-primary-400 text-sm font-medium">
                          {formatTime(event.start)}
                        </span>
                        <div className="w-px h-3 bg-surface-300 my-1" />
                        <span className="text-surface-400 text-xs">
                          {formatTime(event.end)}
                        </span>
                      </div>

                      {/* Event Details */}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-surface-800 font-medium text-sm truncate">
                          {event.summary || 'Untitled Event'}
                        </h3>
                        {event.attendees && event.attendees.length > 0 && (
                          <div className="flex items-center gap-1 mt-1.5 text-surface-400">
                            <Users className="w-3 h-3" />
                            <span className="text-xs truncate">
                              {event.attendees.length} attendee{event.attendees.length > 1 ? 's' : ''}
                            </span>
                          </div>
                        )}
                        {event.description && (
                          <p className="text-surface-400 text-xs mt-1 line-clamp-2">
                            {event.description}
                          </p>
                        )}
                      </div>

                      {/* Duration badge */}
                      <div className="flex items-center gap-1 text-surface-400 text-xs bg-surface-100 px-2 py-1 rounded-lg">
                        <Clock className="w-3 h-3" />
                        {(() => {
                          const start = new Date(event.start)
                          const end = new Date(event.end)
                          const mins = (end.getTime() - start.getTime()) / (1000 * 60)
                          if (mins >= 60) return `${Math.round(mins / 60)}h`
                          return `${mins}m`
                        })()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
