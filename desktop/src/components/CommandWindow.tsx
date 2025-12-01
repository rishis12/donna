import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Send, Mic, MicOff, LogOut, Calendar, Mail, Bell, Check, X } from 'lucide-react'

export default function CommandWindow() {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { messages, isLoading, isRecording, sendMessage, startRecording, stopRecording, logout, confirmAction } = useAppStore()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    await sendMessage(input.trim())
    setInput('')
  }

  const handleMicClick = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const getIntentIcon = (intent?: string) => {
    switch (intent) {
      case 'schedule_event':
      case 'move_event':
      case 'get_schedule':
        return <Calendar className="w-3 h-3" />
      case 'draft_email':
      case 'send_email':
        return <Mail className="w-3 h-3" />
      case 'create_reminder':
        return <Bell className="w-3 h-3" />
      default:
        return null
    }
  }

  return (
    <div className="w-full max-w-lg animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 px-1">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-surface-200/60 text-xs uppercase tracking-wider">Agent Active</span>
        </div>
        <button
          onClick={logout}
          className="p-2 text-surface-200/40 hover:text-surface-100 transition-colors"
          title="Sign out"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="bg-surface-900/80 backdrop-blur-xl border border-surface-700/30 rounded-2xl p-4 mb-4 h-72 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-surface-200/30 text-sm">
            Ask me to set reminders, manage your calendar, or draft emails...
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`animate-slide-up ${msg.role === 'user' ? 'text-right' : ''}`}
              >
                <div
                  className={`inline-block max-w-[85%] px-4 py-2 rounded-2xl ${
                    msg.role === 'user'
                      ? 'bg-accent-500/20 text-accent-100 rounded-br-md'
                      : 'bg-surface-800/60 text-surface-100 rounded-bl-md'
                  }`}
                >
                  {msg.intent && (
                    <div className="flex items-center gap-1.5 text-xs text-surface-200/50 mb-1">
                      {getIntentIcon(msg.intent)}
                      <span>{msg.intent.replace('_', ' ')}</span>
                    </div>
                  )}
                  <p className="text-sm">{msg.content}</p>
                  
                  {msg.requiresConfirmation && msg.actionId && (
                    <div className="flex gap-2 mt-2 pt-2 border-t border-surface-700/30">
                      <button
                        onClick={() => confirmAction(msg.actionId!, true)}
                        className="flex items-center gap-1 px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-lg text-xs hover:bg-emerald-500/30 transition-colors"
                      >
                        <Check className="w-3 h-3" /> Confirm
                      </button>
                      <button
                        onClick={() => confirmAction(msg.actionId!, false)}
                        className="flex items-center gap-1 px-3 py-1 bg-red-500/20 text-red-400 rounded-lg text-xs hover:bg-red-500/30 transition-colors"
                      >
                        <X className="w-3 h-3" /> Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-1 px-4 py-2">
                <div className="w-2 h-2 rounded-full bg-accent-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-accent-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-accent-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="relative">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything..."
          className="w-full bg-surface-900/80 backdrop-blur-xl border border-surface-700/30 rounded-2xl py-4 pl-5 pr-24 text-surface-100 placeholder:text-surface-200/30 focus:outline-none focus:border-accent-500/50 focus:ring-2 focus:ring-accent-500/10 transition-all"
          disabled={isLoading}
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          <button
            type="button"
            onClick={handleMicClick}
            className={`p-2.5 rounded-xl transition-all ${
              isRecording
                ? 'bg-red-500 text-white animate-pulse'
                : 'text-surface-200/40 hover:text-surface-100 hover:bg-surface-800/50'
            }`}
          >
            {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          </button>
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="p-2.5 bg-accent-500 hover:bg-accent-400 disabled:bg-surface-700 disabled:text-surface-200/30 text-white rounded-xl transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  )
}

