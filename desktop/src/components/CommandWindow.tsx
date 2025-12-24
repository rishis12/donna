import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Send, Mic, MicOff, LogOut, Calendar, Mail, Bell, Check, X, Settings, Copy, CheckCheck, RotateCcw, Sparkles, MessageSquare } from 'lucide-react'
import SettingsPanel from './SettingsPanel'
import SchedulePanel from './SchedulePanel'

type Tab = 'chat' | 'schedule'

export default function CommandWindow() {
  const [input, setInput] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { messages, isLoading, isRecording, sendMessage, startRecording, stopRecording, logout, confirmAction, clearMessages, clearHistory } = useAppStore()

  const copyConversation = async () => {
    const transcript = messages.map(msg => {
      const role = msg.role === 'user' ? 'You' : 'Donna'
      const intent = msg.intent ? ` [${msg.intent}]` : ''
      return `${role}${intent}: ${msg.content}`
    }).join('\n\n')
    
    await navigator.clipboard.writeText(transcript)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    // Focus input on load
    inputRef.current?.focus()
  }, [])

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
        return <Calendar className="w-3.5 h-3.5" />
      case 'draft_email':
      case 'send_email':
        return <Mail className="w-3.5 h-3.5" />
      case 'create_reminder':
        return <Bell className="w-3.5 h-3.5" />
      default:
        return null
    }
  }

  const getIntentLabel = (intent?: string) => {
    switch (intent) {
      case 'schedule_event': return 'Scheduling'
      case 'move_event': return 'Rescheduling'
      case 'get_schedule': return 'Calendar'
      case 'draft_email': return 'Drafting'
      case 'send_email': return 'Sending'
      case 'create_reminder': return 'Reminder'
      default: return null
    }
  }

  return (
    <div className="w-full max-w-lg animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-surface-900" />
          </div>
          <div>
            <h1 className="text-surface-100 font-semibold text-sm tracking-tight">Donna</h1>
            <p className="text-surface-200/50 text-xs">Your executive assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={clearHistory}
            className="p-2 text-surface-200/40 hover:text-surface-100 hover:bg-surface-800/50 rounded-lg transition-all"
            title="New conversation"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={copyConversation}
            className={`p-2 rounded-lg transition-all ${copied ? 'text-emerald-400 bg-emerald-500/10' : 'text-surface-200/40 hover:text-surface-100 hover:bg-surface-800/50'}`}
            title={copied ? 'Copied!' : 'Copy conversation'}
            disabled={messages.length === 0}
          >
            {copied ? <CheckCheck className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setShowSettings(true)}
            className="p-2 text-surface-200/40 hover:text-surface-100 hover:bg-surface-800/50 rounded-lg transition-all"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
          <button
            onClick={logout}
            className="p-2 text-surface-200/40 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      <SettingsPanel isOpen={showSettings} onClose={() => setShowSettings(false)} />

      {/* Tabs */}
      <div className="flex gap-1 mb-3 bg-surface-900/50 p-1 rounded-xl">
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'chat'
              ? 'bg-surface-800 text-surface-100 shadow-md'
              : 'text-surface-400 hover:text-surface-200'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Chat
        </button>
        <button
          onClick={() => setActiveTab('schedule')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'schedule'
              ? 'bg-surface-800 text-surface-100 shadow-md'
              : 'text-surface-400 hover:text-surface-200'
          }`}
        >
          <Calendar className="w-4 h-4" />
          Schedule
        </button>
      </div>

      {/* Content Area */}
      <div className="bg-surface-900/90 backdrop-blur-xl border border-surface-700/40 rounded-2xl p-4 mb-3 h-80 overflow-hidden shadow-xl shadow-black/20">
        {activeTab === 'schedule' ? (
          <SchedulePanel />
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-6">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-amber-400/20 to-orange-500/20 flex items-center justify-center mb-3">
              <Sparkles className="w-6 h-6 text-amber-400" />
            </div>
            <p className="text-surface-200/60 text-sm mb-1">Hey, I'm Donna.</p>
            <p className="text-surface-200/40 text-xs">Ask me to schedule meetings, set reminders, or draft emails.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`animate-slide-up ${msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}`}
              >
                <div
                  className={`max-w-[85%] px-4 py-2.5 rounded-2xl ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-accent-500/30 to-accent-600/20 text-accent-50 rounded-br-md border border-accent-500/20'
                      : 'bg-surface-800/80 text-surface-100 rounded-bl-md border border-surface-700/30'
                  }`}
                >
                  {msg.intent && getIntentLabel(msg.intent) && (
                    <div className="flex items-center gap-1.5 text-xs text-amber-400/80 mb-1.5 font-medium">
                      {getIntentIcon(msg.intent)}
                      <span>{getIntentLabel(msg.intent)}</span>
                    </div>
                  )}
                  <p className="text-sm leading-relaxed">{msg.content}</p>
                  
                  {msg.requiresConfirmation && msg.actionId && (
                    <div className="flex gap-2 mt-3 pt-2.5 border-t border-surface-700/40">
                      <button
                        onClick={() => confirmAction(msg.actionId!, true)}
                        className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-xl text-xs font-medium hover:bg-emerald-500/30 transition-all border border-emerald-500/20"
                      >
                        <Check className="w-3.5 h-3.5" /> Do it
                      </button>
                      <button
                        onClick={() => confirmAction(msg.actionId!, false)}
                        className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 bg-surface-700/50 text-surface-300 rounded-xl text-xs font-medium hover:bg-surface-700/70 transition-all border border-surface-600/30"
                      >
                        <X className="w-3.5 h-3.5" /> Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-surface-800/80 rounded-2xl rounded-bl-md px-4 py-3 border border-surface-700/30">
                  <div className="flex gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input - only show in chat mode */}
      {activeTab === 'chat' && (
        <>
          <form onSubmit={handleSubmit} className="relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Donna..."
              className="w-full bg-surface-900/90 backdrop-blur-xl border border-surface-700/40 rounded-2xl py-4 pl-5 pr-28 text-surface-100 placeholder:text-surface-200/40 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/10 transition-all shadow-lg shadow-black/10"
              disabled={isLoading}
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <button
                type="button"
                onClick={handleMicClick}
                className={`p-2.5 rounded-xl transition-all ${
                  isRecording
                    ? 'bg-red-500 text-white animate-pulse shadow-lg shadow-red-500/30'
                    : 'text-surface-200/40 hover:text-surface-100 hover:bg-surface-800/50'
                }`}
                title={isRecording ? 'Stop recording' : 'Voice input'}
              >
                {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="p-2.5 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 disabled:from-surface-700 disabled:to-surface-700 disabled:text-surface-200/30 text-white rounded-xl transition-all shadow-lg shadow-amber-500/20 disabled:shadow-none"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>

          {/* Quick Tips */}
          <div className="mt-3 flex items-center justify-center gap-2 text-xs text-surface-200/30">
            <span>Try:</span>
            <button 
              onClick={() => setInput("Schedule a meeting")}
              className="px-2 py-0.5 bg-surface-800/30 rounded-md hover:bg-surface-800/50 hover:text-surface-200/50 transition-all"
            >
              Schedule a meeting
            </button>
            <button 
              onClick={() => setInput("Remind me at 5pm")}
              className="px-2 py-0.5 bg-surface-800/30 rounded-md hover:bg-surface-800/50 hover:text-surface-200/50 transition-all"
            >
              Set reminder
            </button>
          </div>
        </>
      )}
    </div>
  )
}

