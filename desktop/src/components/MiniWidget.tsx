import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Send, Maximize2, MessageSquare, CheckSquare, Plus, X, Check, Mail } from 'lucide-react'

export default function MiniWidget() {
  const [input, setInput] = useState('')
  const [todoInput, setTodoInput] = useState('')
  const [showTodoInput, setShowTodoInput] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const todoInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const { 
    messages, 
    isLoading, 
    sendMessage, 
    confirmAction,
    sendEmail,
    toggleMiniMode, 
    widgetMode, 
    setWidgetMode,
    todos,
    addTodo,
    toggleTodo,
    removeTodo,
  } = useAppStore()

  useEffect(() => {
    if (widgetMode === 'chat') {
      inputRef.current?.focus()
    }
  }, [widgetMode])

  useEffect(() => {
    if (showTodoInput) {
      todoInputRef.current?.focus()
    }
  }, [showTodoInput])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    await sendMessage(input.trim())
    setInput('')
  }

  const handleAddTodo = (e: React.FormEvent) => {
    e.preventDefault()
    if (!todoInput.trim()) return
    addTodo(todoInput.trim())
    setTodoInput('')
    setShowTodoInput(false)
  }

  const incompleteTodos = todos.filter(t => !t.completed)
  const completedTodos = todos.filter(t => t.completed)
  
  // Show last 5 messages in mini widget
  const recentMessages = messages.slice(-5)

  return (
    <div className="h-screen w-screen bg-white flex flex-col overflow-hidden">
      {/* Header - draggable */}
      <div 
        className="flex items-center justify-between px-2 py-1 bg-surface-50 border-b border-surface-200"
        data-tauri-drag-region
      >
        <div className="flex items-center gap-1" data-tauri-drag-region>
          <span className="text-xs">☕</span>
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => setWidgetMode('chat')}
            className={`p-0.5 rounded ${
              widgetMode === 'chat' 
                ? 'bg-primary-100 text-primary-500' 
                : 'text-surface-400 hover:text-surface-600'
            }`}
            title="Chat"
          >
            <MessageSquare className="w-3 h-3" />
          </button>
          <button
            onClick={() => setWidgetMode('todos')}
            className={`p-0.5 rounded relative ${
              widgetMode === 'todos' 
                ? 'bg-primary-100 text-primary-500' 
                : 'text-surface-400 hover:text-surface-600'
            }`}
            title="Tasks"
          >
            <CheckSquare className="w-3 h-3" />
            {incompleteTodos.length > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-primary-400 rounded-full"></span>
            )}
          </button>
          <button
            onClick={toggleMiniMode}
            className="p-0.5 text-surface-400 hover:text-surface-600 rounded ml-0.5"
            title="Expand"
          >
            <Maximize2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {widgetMode === 'chat' ? (
          <div className="h-full flex flex-col p-1.5">
            {/* Messages area */}
            <div className="flex-1 overflow-y-auto mb-1.5 space-y-1">
              {recentMessages.length === 0 ? (
                <p className="text-xs text-surface-400 text-center py-2">Start chatting...</p>
              ) : (
                recentMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] px-1.5 py-1 rounded text-xs ${
                        msg.role === 'user'
                          ? 'bg-primary-400 text-white rounded-br-sm'
                          : 'bg-surface-50 text-surface-700 rounded-bl-sm border border-surface-200'
                      }`}
                    >
                      <p className="leading-relaxed break-words">{msg.content}</p>
                      
                      {msg.requiresConfirmation && msg.actionId && (
                        <div className="flex gap-1 mt-1 pt-1 border-t border-surface-200">
                          <button
                            onClick={() => confirmAction(msg.actionId!, true)}
                            className="flex-1 px-1.5 py-0.5 bg-success-400 text-white rounded text-xs hover:bg-success-500 transition-all"
                          >
                            Do it
                          </button>
                          <button
                            onClick={() => confirmAction(msg.actionId!, false)}
                            className="flex-1 px-1.5 py-0.5 bg-surface-100 text-surface-600 rounded text-xs hover:bg-surface-200 transition-all"
                          >
                            Cancel
                          </button>
                        </div>
                      )}
                      {msg.intent === 'draft_email' && msg.emailEntities && !msg.requiresConfirmation && (
                        <button
                          onClick={() => sendEmail(msg.emailEntities!.to, msg.emailEntities!.subject, msg.emailEntities!.body)}
                          className="w-full mt-1 pt-1 border-t border-surface-200 px-1.5 py-0.5 bg-primary-400 text-white rounded text-xs hover:bg-primary-500 transition-all"
                        >
                          📧 Send Email
                        </button>
                      )}
                      {msg.intent === 'draft_email' && msg.emailEntities && !msg.requiresConfirmation && (
                        <button
                          onClick={() => sendEmail(msg.emailEntities!.to, msg.emailEntities!.subject, msg.emailEntities!.body)}
                          className="w-full mt-1 pt-1 border-t border-surface-200 px-1.5 py-0.5 bg-primary-400 text-white rounded text-xs hover:bg-primary-500 transition-all"
                        >
                          📧 Send Email
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-surface-50 rounded px-1.5 py-1 border border-surface-200">
                    <div className="flex gap-0.5">
                      <div className="w-1 h-1 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-1 h-1 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-1 h-1 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask..."
                className="w-full bg-surface-50 border border-surface-200 rounded py-1.5 pl-2 pr-7 text-xs text-surface-700 placeholder:text-surface-400 focus:outline-none focus:border-primary-400 transition-all"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="absolute right-0.5 top-1/2 -translate-y-1/2 p-1 bg-primary-400 hover:bg-primary-500 disabled:bg-surface-200 text-white rounded transition-all"
              >
                <Send className="w-2.5 h-2.5" />
              </button>
            </form>
          </div>
        ) : (
          <div className="h-full flex flex-col p-1.5">
            {/* Add Todo Input */}
            {showTodoInput ? (
              <form onSubmit={handleAddTodo} className="mb-1 flex gap-0.5">
                <input
                  ref={todoInputRef}
                  type="text"
                  value={todoInput}
                  onChange={(e) => setTodoInput(e.target.value)}
                  placeholder="New task..."
                  className="flex-1 bg-surface-50 border border-surface-200 rounded py-1 px-1.5 text-xs text-surface-700 placeholder:text-surface-400 focus:outline-none focus:border-primary-400"
                />
                <button
                  type="submit"
                  disabled={!todoInput.trim()}
                  className="p-1 bg-primary-400 hover:bg-primary-500 disabled:bg-surface-200 text-white rounded transition-all"
                >
                  <Check className="w-2.5 h-2.5" />
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowTodoInput(false)
                    setTodoInput('')
                  }}
                  className="p-1 text-surface-400 hover:text-surface-600 rounded transition-all"
                >
                  <X className="w-2.5 h-2.5" />
                </button>
              </form>
            ) : (
              <button
                onClick={() => setShowTodoInput(true)}
                className="w-full mb-1 flex items-center justify-center gap-1 py-1 text-xs text-surface-500 hover:text-surface-700 bg-surface-50 hover:bg-surface-100 border border-dashed border-surface-300 rounded transition-all"
              >
                <Plus className="w-2.5 h-2.5" />
                Add
              </button>
            )}

            {/* Todo List - scrollable */}
            <div className="flex-1 overflow-y-auto">
              {incompleteTodos.length === 0 && completedTodos.length === 0 ? (
                <div className="text-center py-2">
                  <p className="text-xs text-surface-400">No tasks</p>
                </div>
              ) : (
                <div className="space-y-0.5">
                  {incompleteTodos.map(todo => (
                    <div key={todo.id} className="flex items-center gap-1 p-1 rounded hover:bg-surface-50 group">
                      <button
                        onClick={() => toggleTodo(todo.id)}
                        className="w-3 h-3 rounded border border-surface-300 hover:border-primary-400 shrink-0 transition-all"
                      />
                      <span className="flex-1 text-xs text-surface-700 truncate">{todo.text}</span>
                      <button
                        onClick={() => removeTodo(todo.id)}
                        className="p-0.5 text-surface-300 hover:text-surface-500 opacity-0 group-hover:opacity-100 transition-all"
                        title="Delete"
                      >
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </div>
                  ))}
                  {completedTodos.length > 0 && (
                    <>
                      <div className="pt-1 pb-0.5">
                        <span className="text-xs text-surface-400">Done ({completedTodos.length})</span>
                      </div>
                      {completedTodos.slice(0, 2).map(todo => (
                        <div key={todo.id} className="flex items-center gap-1 p-1 rounded hover:bg-surface-50 group opacity-50">
                          <button
                            onClick={() => toggleTodo(todo.id)}
                            className="w-3 h-3 rounded bg-success-400 flex items-center justify-center shrink-0"
                          >
                            <Check className="w-2 h-2 text-white" />
                          </button>
                          <span className="flex-1 text-xs text-surface-500 line-through truncate">{todo.text}</span>
                          <button
                            onClick={() => removeTodo(todo.id)}
                            className="p-0.5 text-surface-300 hover:text-surface-500 opacity-0 group-hover:opacity-100 transition-all"
                            title="Delete"
                          >
                            <X className="w-2.5 h-2.5" />
                          </button>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
