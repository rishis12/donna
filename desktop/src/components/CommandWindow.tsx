import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Send, Mic, MicOff, LogOut, Calendar, Mail, Bell, Check, X, Settings, Copy, CheckCheck, RotateCcw, MessageSquare, Minimize2, CheckSquare, Plus, Sun } from 'lucide-react'
import SettingsPanel from './SettingsPanel'
import SchedulePanel from './SchedulePanel'
import TodoPanel from './TodoPanel'
import DigestPanel from './DigestPanel'

type Tab = 'chat' | 'schedule' | 'todos' | 'digest'

export default function CommandWindow() {
  const [input, setInput] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { messages, isLoading, isRecording, sendMessage, startRecording, stopRecording, logout, confirmAction, sendEmail, clearHistory, toggleMiniMode } = useAppStore()

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
    <div className="w-full max-w-2xl animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 px-1">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-2xl bg-primary-50 flex items-center justify-center">
              <span className="text-xl">☕</span>
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-success-400 border-2 border-white" />
          </div>
          <div>
            <h1 className="text-surface-800 font-semibold text-base">Donna</h1>
            <p className="text-surface-500 text-xs">Your personal assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={toggleMiniMode}
            className="p-2.5 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-xl transition-all"
            title="Mini mode"
          >
            <Minimize2 className="w-4 h-4" />
          </button>
          <button
            onClick={clearHistory}
            className="p-2.5 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-xl transition-all"
            title="New conversation"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={copyConversation}
            className={`p-2.5 rounded-xl transition-all ${copied ? 'text-success-400 bg-success-400/10' : 'text-surface-400 hover:text-surface-600 hover:bg-surface-100'}`}
            title={copied ? 'Copied!' : 'Copy conversation'}
            disabled={messages.length === 0}
          >
            {copied ? <CheckCheck className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setShowSettings(true)}
            className="p-2.5 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-xl transition-all"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
          <button
            onClick={logout}
            className="p-2.5 text-surface-400 hover:text-error-400 hover:bg-error-400/10 rounded-xl transition-all"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      <SettingsPanel isOpen={showSettings} onClose={() => setShowSettings(false)} />

      {/* Tabs */}
      <div className="flex gap-1.5 mb-4 bg-surface-100 p-1.5 rounded-2xl">
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-sm font-medium transition-all ${
            activeTab === 'chat'
              ? 'bg-white text-surface-800 shadow-sm'
              : 'text-surface-500 hover:text-surface-700'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Chat
        </button>
        <button
          onClick={() => setActiveTab('digest')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-sm font-medium transition-all ${
            activeTab === 'digest'
              ? 'bg-white text-surface-800 shadow-sm'
              : 'text-surface-500 hover:text-surface-700'
          }`}
        >
          <Sun className="w-4 h-4" />
          Today
        </button>
        <button
          onClick={() => setActiveTab('schedule')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-sm font-medium transition-all ${
            activeTab === 'schedule'
              ? 'bg-white text-surface-800 shadow-sm'
              : 'text-surface-500 hover:text-surface-700'
          }`}
        >
          <Calendar className="w-4 h-4" />
          Week
        </button>
        <button
          onClick={() => setActiveTab('todos')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-sm font-medium transition-all ${
            activeTab === 'todos'
              ? 'bg-white text-surface-800 shadow-sm'
              : 'text-surface-500 hover:text-surface-700'
          }`}
        >
          <CheckSquare className="w-4 h-4" />
          Tasks
        </button>
      </div>

      {/* Content Area */}
      <div className="bg-white border border-surface-200 rounded-3xl p-5 mb-4 h-96 overflow-y-auto shadow-lg shadow-surface-200/50">
        {activeTab === 'schedule' ? (
          <SchedulePanel />
        ) : activeTab === 'todos' ? (
          <TodoPanel />
        ) : activeTab === 'digest' ? (
          <DigestPanel />
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-6">
            <div className="w-14 h-14 rounded-2xl bg-primary-50 flex items-center justify-center mb-4">
              <span className="text-2xl">☕</span>
            </div>
            <p className="text-surface-700 text-sm font-medium mb-1">Hey, I'm Donna!</p>
            <p className="text-surface-400 text-sm">Ask me to schedule meetings, set reminders, or draft emails.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`animate-slide-up ${msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}`}
              >
                <div
                  className={`max-w-[85%] px-4 py-3 rounded-2xl ${
                    msg.role === 'user'
                      ? 'bg-primary-400 text-white rounded-br-md'
                      : 'bg-surface-50 text-surface-800 rounded-bl-md border border-surface-200'
                  }`}
                >
                  {msg.intent && getIntentLabel(msg.intent) && (
                    <div className={`flex items-center gap-1.5 text-xs mb-2 font-medium ${msg.role === 'user' ? 'text-white/80' : 'text-primary-400'}`}>
                      {getIntentIcon(msg.intent)}
                      <span>{getIntentLabel(msg.intent)}</span>
                    </div>
                  )}
                  <p className="text-sm leading-relaxed">{msg.content}</p>
                  
                  {msg.requiresConfirmation && msg.actionId && (
                    <div className="flex gap-2 mt-3 pt-3 border-t border-surface-200">
                      <button
                        onClick={() => confirmAction(msg.actionId!, true)}
                        className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-success-400 text-white rounded-xl text-xs font-medium hover:bg-success-500 transition-all"
                      >
                        <Check className="w-3.5 h-3.5" /> Do it
                      </button>
                      <button
                        onClick={() => confirmAction(msg.actionId!, false)}
                        className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-surface-100 text-surface-600 rounded-xl text-xs font-medium hover:bg-surface-200 transition-all"
                      >
                        <X className="w-3.5 h-3.5" /> Cancel
                      </button>
                    </div>
                  )}
                  {msg.intent === 'draft_email' && msg.emailEntities && !msg.requiresConfirmation && (
                    <div className="flex gap-2 mt-3 pt-3 border-t border-surface-200">
                      <button
                        onClick={() => sendEmail(msg.emailEntities!.to, msg.emailEntities!.subject, msg.emailEntities!.body)}
                        className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-primary-400 text-white rounded-xl text-xs font-medium hover:bg-primary-500 transition-all"
                      >
                        <Mail className="w-3.5 h-3.5" /> Send Email
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-surface-50 rounded-2xl rounded-bl-md px-4 py-3 border border-surface-200">
                  <div className="flex gap-1.5 items-center">
                    <div className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                    <span className="text-xs text-surface-400 ml-2">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      {activeTab === 'chat' && (
        <>
          <form onSubmit={handleSubmit} className="relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Donna..."
              className="w-full bg-white border border-surface-200 rounded-2xl py-4 pl-5 pr-28 text-surface-800 placeholder:text-surface-400 focus:outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all shadow-sm"
              disabled={isLoading}
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <button
                type="button"
                onClick={handleMicClick}
                className={`p-2.5 rounded-xl transition-all ${
                  isRecording
                    ? 'bg-error-400 text-white animate-pulse'
                    : 'text-surface-400 hover:text-surface-600 hover:bg-surface-100'
                }`}
                title={isRecording ? 'Stop recording' : 'Voice input'}
              >
                {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="p-2.5 bg-primary-400 hover:bg-primary-500 disabled:bg-surface-200 disabled:text-surface-400 text-white rounded-xl transition-all"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>

          {/* Quick Tips */}
          <div className="mt-3 flex items-center justify-center gap-2 text-xs text-surface-400">
            <span>Try:</span>
            <button 
              onClick={() => setInput("Schedule a meeting")}
              className="px-2.5 py-1 bg-surface-100 rounded-lg hover:bg-surface-200 hover:text-surface-600 transition-all"
            >
              Schedule a meeting
            </button>
            <button 
              onClick={() => setInput("Remind me at 5pm")}
              className="px-2.5 py-1 bg-surface-100 rounded-lg hover:bg-surface-200 hover:text-surface-600 transition-all"
            >
              Set reminder
            </button>
          </div>
        </>
      )}
    </div>
  )
}
