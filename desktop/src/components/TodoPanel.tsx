import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Check, Plus, X, CheckSquare } from 'lucide-react'

export default function TodoPanel() {
  const [newTodoText, setNewTodoText] = useState('')
  const [isAdding, setIsAdding] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const { todos, addTodo, toggleTodo, removeTodo } = useAppStore()

  useEffect(() => {
    if (isAdding) {
      inputRef.current?.focus()
    }
  }, [isAdding])

  const handleAddTodo = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTodoText.trim()) return
    addTodo(newTodoText.trim())
    setNewTodoText('')
    setIsAdding(false)
  }

  const incompleteTodos = todos.filter(t => !t.completed)
  const completedTodos = todos.filter(t => t.completed)

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-surface-800 font-semibold flex items-center gap-2">
          <CheckSquare className="w-4 h-4 text-primary-400" />
          Your Tasks
        </h2>
        <span className="text-xs text-surface-400">
          {incompleteTodos.length} remaining
        </span>
      </div>

      {/* Add Todo */}
      {isAdding ? (
        <form onSubmit={handleAddTodo} className="flex gap-2 mb-4">
          <input
            ref={inputRef}
            type="text"
            value={newTodoText}
            onChange={(e) => setNewTodoText(e.target.value)}
            placeholder="What needs to be done?"
            className="flex-1 bg-surface-50 border border-surface-200 rounded-xl py-2.5 px-4 text-sm text-surface-700 placeholder:text-surface-400 focus:outline-none focus:border-primary-400"
          />
          <button
            type="submit"
            disabled={!newTodoText.trim()}
            className="px-4 py-2 bg-primary-400 hover:bg-primary-500 disabled:bg-surface-200 text-white rounded-xl text-sm font-medium transition-all"
          >
            Add
          </button>
          <button
            type="button"
            onClick={() => setIsAdding(false)}
            className="p-2.5 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-xl transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </form>
      ) : (
        <button
          onClick={() => setIsAdding(true)}
          className="w-full mb-4 flex items-center justify-center gap-2 py-3 px-4 text-sm text-surface-500 hover:text-surface-700 bg-surface-50 hover:bg-surface-100 border border-dashed border-surface-300 rounded-xl transition-all"
        >
          <Plus className="w-4 h-4" />
          Add a task
        </button>
      )}

      {/* Todo List */}
      <div className="flex-1 overflow-y-auto">
        {incompleteTodos.length === 0 && completedTodos.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <div className="w-12 h-12 rounded-2xl bg-surface-100 flex items-center justify-center mb-3">
              <Check className="w-6 h-6 text-surface-400" />
            </div>
            <p className="text-surface-600 text-sm font-medium">All caught up!</p>
            <p className="text-surface-400 text-xs mt-1">Add tasks to stay organized</p>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Incomplete todos */}
            {incompleteTodos.map(todo => (
              <div
                key={todo.id}
                className="flex items-center gap-3 p-3 bg-surface-50 hover:bg-surface-100 border border-surface-200 rounded-xl group transition-all"
              >
                <button
                  onClick={() => toggleTodo(todo.id)}
                  className="w-5 h-5 rounded-md border-2 border-surface-300 hover:border-primary-400 flex items-center justify-center transition-all shrink-0"
                />
                <span className="flex-1 text-sm text-surface-700">{todo.text}</span>
                <button
                  onClick={() => removeTodo(todo.id)}
                  className="p-1 text-surface-300 hover:text-surface-500 opacity-0 group-hover:opacity-100 transition-all"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}

            {/* Completed section */}
            {completedTodos.length > 0 && (
              <>
                <div className="pt-3 pb-1">
                  <span className="text-xs text-surface-400 font-medium uppercase tracking-wider">
                    Completed ({completedTodos.length})
                  </span>
                </div>
                {completedTodos.map(todo => (
                  <div
                    key={todo.id}
                    className="flex items-center gap-3 p-3 bg-surface-50/50 border border-surface-200/50 rounded-xl group transition-all opacity-60"
                  >
                    <button
                      onClick={() => toggleTodo(todo.id)}
                      className="w-5 h-5 rounded-md bg-success-400 flex items-center justify-center shrink-0"
                    >
                      <Check className="w-3 h-3 text-white" />
                    </button>
                    <span className="flex-1 text-sm text-surface-500 line-through">{todo.text}</span>
                    <button
                      onClick={() => removeTodo(todo.id)}
                      className="p-1 text-surface-300 hover:text-surface-500 opacity-0 group-hover:opacity-100 transition-all"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

