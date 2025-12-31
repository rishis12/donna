import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Calendar, Bell, RefreshCw, Sun, Clock, Users, Mail, MessageSquare } from 'lucide-react'

export default function DigestPanel() {
  const { dailyDigest, fetchDailyDigest, user, messages } = useAppStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDigest()
  }, [])

  // Refresh digest when messages change (in case a reminder was just created)
  useEffect(() => {
    const lastMessage = messages[messages.length - 1]
    if (lastMessage?.content?.toLowerCase().includes('reminder') || 
        lastMessage?.intent === 'create_reminder') {
      const timer = setTimeout(() => {
        loadDigest()
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [messages])

  const loadDigest = async () => {
    setLoading(true)
    await fetchDailyDigest()
    setLoading(false)
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
  }

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })

  const getTimeOfDay = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'morning'
    if (hour < 17) return 'afternoon'
    return 'evening'
  }

  if (!user?.googleConnected) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center px-6">
        <div className="w-14 h-14 rounded-2xl bg-surface-100 flex items-center justify-center mb-4">
          <Sun className="w-7 h-7 text-surface-400" />
        </div>
        <p className="text-surface-600 text-sm font-medium mb-1">Connect Your Calendar</p>
        <p className="text-surface-400 text-sm">Connect your Google account in Settings to see your daily digest.</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <RefreshCw className="w-6 h-6 text-primary-400 animate-spin" />
      </div>
    )
  }

  const hasUnread = (dailyDigest?.unreadEmails || 0) > 0 || (dailyDigest?.unreadTeams || 0) > 0

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-surface-800 font-semibold text-lg">Good {getTimeOfDay()}!</h2>
        <p className="text-surface-400 text-sm">{today}</p>
      </div>

      {/* Summary */}
      <div className="bg-primary-50 rounded-xl p-4 mb-4">
        <p className="text-surface-700 text-sm">
          {dailyDigest?.summary || "You're all set for today!"}
        </p>
      </div>

      {/* Communications Summary */}
      {hasUnread && dailyDigest?.communicationsSummary && (
        <div className="bg-surface-50 border border-surface-200 rounded-xl p-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Mail className="w-4 h-4 text-primary-400" />
            <span className="text-sm font-medium text-surface-700">Your Inbox Briefing</span>
          </div>
          <p className="text-sm text-surface-600 leading-relaxed whitespace-pre-wrap">
            {dailyDigest.communicationsSummary}
          </p>
          <div className="flex items-center gap-4 mt-3 pt-3 border-t border-surface-200 text-xs text-surface-400">
            {(dailyDigest.unreadEmailsGmail || 0) > 0 && (
              <span>📧 {dailyDigest.unreadEmailsGmail} Gmail</span>
            )}
            {(dailyDigest.unreadEmailsOutlook || 0) > 0 && (
              <span>📧 {dailyDigest.unreadEmailsOutlook} Outlook</span>
            )}
            {(dailyDigest.unreadTeams || 0) > 0 && (
              <span>💬 {dailyDigest.unreadTeams} Teams</span>
            )}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {/* Meetings */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-primary-400" />
              <span className="text-sm font-medium text-surface-700">Today's Meetings</span>
            </div>
            <span className="text-xs bg-surface-100 text-surface-500 px-2 py-0.5 rounded-full">
              {dailyDigest?.meetingsCount || 0}
            </span>
          </div>
          
          {dailyDigest?.meetings && dailyDigest.meetings.length > 0 ? (
            <div className="space-y-2">
              {dailyDigest.meetings.map(meeting => (
                <div key={meeting.id} className="flex items-center gap-3 p-3 bg-surface-50 border border-surface-200 rounded-xl">
                  <div className="text-primary-400">
                    <Clock className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-surface-700 font-medium truncate">{meeting.summary}</p>
                    <p className="text-xs text-surface-400">{formatTime(meeting.start)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 bg-surface-50 border border-surface-200 rounded-xl text-center">
              <p className="text-sm text-surface-400">No meetings today</p>
            </div>
          )}
        </div>

        {/* Reminders */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-primary-400" />
              <span className="text-sm font-medium text-surface-700">Reminders</span>
            </div>
            <span className="text-xs bg-surface-100 text-surface-500 px-2 py-0.5 rounded-full">
              {dailyDigest?.remindersCount || 0}
            </span>
          </div>
          
          {dailyDigest?.reminders && dailyDigest.reminders.length > 0 ? (
            <div className="space-y-2">
              {dailyDigest.reminders.map(reminder => (
                <div key={reminder.id} className="flex items-center gap-3 p-3 bg-surface-50 border border-surface-200 rounded-xl">
                  <div className="w-2 h-2 rounded-full bg-primary-400" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-surface-700 truncate">{reminder.text}</p>
                    <p className="text-xs text-surface-400">{formatTime(reminder.dueTime)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 bg-surface-50 border border-surface-200 rounded-xl text-center">
              <p className="text-sm text-surface-400">No reminders today</p>
            </div>
          )}
        </div>
      </div>

      {/* Refresh */}
      <button
        onClick={loadDigest}
        className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 text-sm text-surface-500 hover:text-surface-700 bg-surface-50 hover:bg-surface-100 rounded-xl transition-all"
      >
        <RefreshCw className="w-4 h-4" />
        Refresh
      </button>
    </div>
  )
}
