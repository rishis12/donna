import { useEffect, useRef } from 'react'
import CommandWindow from './components/CommandWindow'
import LoginForm from './components/LoginForm'
import Onboarding from './components/Onboarding'
import MiniWidget from './components/MiniWidget'
import { useAppStore } from './stores/appStore'

function App() {
  const { isAuthenticated, user, checkAuth, pollDueReminders, isMiniMode } = useAppStore()
  const pollIntervalRef = useRef<number | null>(null)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  useEffect(() => {
    if (isAuthenticated) {
      const { pollDueReminders, pollUpcomingMeetings } = useAppStore.getState()
      pollDueReminders()
      pollUpcomingMeetings()
      pollIntervalRef.current = window.setInterval(() => {
        pollDueReminders()
        pollUpcomingMeetings()
      }, 30000) // Poll every 30 seconds
    }
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [isAuthenticated])

  // Mini mode - compact floating widget that fills the small window
  if (isAuthenticated && isMiniMode) {
    return <MiniWidget />
  }

  return (
    <div className="min-h-screen bg-surface-50 relative overflow-hidden">
      {/* Subtle warm gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-surface-50 via-primary-50/20 to-surface-100" />
      
      {/* Soft decorative shapes */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-primary-200/30 rounded-full blur-3xl -translate-y-1/3 translate-x-1/3" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-surface-300/40 rounded-full blur-3xl translate-y-1/3 -translate-x-1/3" />
      
      {/* Main content */}
      <div className="relative z-10 flex items-center justify-center min-h-screen p-6">
        {!isAuthenticated ? (
          <LoginForm />
        ) : user && !user.onboardingComplete ? (
          <Onboarding />
        ) : (
          <CommandWindow />
        )}
      </div>
    </div>
  )
}

export default App
