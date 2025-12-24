import { useEffect, useRef } from 'react'
import CommandWindow from './components/CommandWindow'
import LoginForm from './components/LoginForm'
import { useAppStore } from './stores/appStore'

function App() {
  const { isAuthenticated, checkAuth, pollDueReminders } = useAppStore()
  const pollIntervalRef = useRef<number | null>(null)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  // Start polling for due reminders when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      // Poll immediately
      pollDueReminders()
      // Then poll every 30 seconds
      pollIntervalRef.current = window.setInterval(pollDueReminders, 30000)
    }
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [isAuthenticated, pollDueReminders])

  return (
    <div className="min-h-screen bg-surface-950 relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-surface-900 via-surface-950 to-black" />
      
      {/* Subtle grid pattern */}
      <div 
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(59, 130, 246, 0.5) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59, 130, 246, 0.5) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }}
      />
      
      {/* Main content */}
      <div className="relative z-10 flex items-center justify-center min-h-screen p-4">
        {isAuthenticated ? <CommandWindow /> : <LoginForm />}
      </div>
    </div>
  )
}

export default App

