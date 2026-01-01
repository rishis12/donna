import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../lib/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  intent?: string
  requiresConfirmation?: boolean
  actionId?: string
  emailEntities?: { to: string; subject: string; body: string } // Store draft email data for sending
}

interface Reminder {
  id: string
  text: string
  dueTime: Date
  status: 'active' | 'completed' | 'cancelled'
}

interface TodoItem {
  id: string
  text: string
  completed: boolean
  createdAt: Date
}

interface DailyDigest {
  meetings: { id: string; summary: string; start: string; end: string }[]
  reminders: { id: string; text: string; dueTime: string }[]
  meetingsCount: number
  remindersCount: number
  unreadEmails: number
  unreadEmailsGmail: number
  unreadEmailsOutlook: number
  unreadTeams: number
  communicationsSummary: string
  summary: string
}

interface AppState {
  isAuthenticated: boolean
  token: string | null
  user: { email: string; googleConnected: boolean; microsoftConnected: boolean; slackConnected: boolean; onboardingComplete: boolean } | null
  messages: Message[]
  reminders: Reminder[]
  todos: TodoItem[]
  dailyDigest: DailyDigest | null
  isLoading: boolean
  isRecording: boolean
  isMiniMode: boolean
  widgetMode: 'chat' | 'todos'
  shownReminderIds: Set<string> // Track shown reminders to prevent duplicates
  
  // Actions
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  loginWithToken: (token: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
  completeOnboarding: () => Promise<void>
  sendMessage: (text: string) => Promise<void>
  confirmAction: (actionId: string, confirmed: boolean) => Promise<void>
  sendEmail: (to: string, subject: string, body: string) => Promise<void>
  startRecording: () => void
  stopRecording: () => Promise<void>
  fetchReminders: () => Promise<void>
  pollDueReminders: () => Promise<void>
  pollUpcomingMeetings: () => Promise<void>
  refreshUser: () => Promise<void>
  clearMessages: () => void
  clearHistory: () => Promise<void>
  // Mini mode & widget
  toggleMiniMode: () => void
  setWidgetMode: (mode: 'chat' | 'todos') => void
  // Todos
  addTodo: (text: string) => void
  toggleTodo: (id: string) => void
  removeTodo: (id: string) => void
  // Daily digest
  fetchDailyDigest: () => Promise<void>
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      token: null,
      user: null,
      messages: [],
      reminders: [],
      todos: [],
      dailyDigest: null,
      isLoading: false,
      isRecording: false,
      isMiniMode: false,
      widgetMode: 'chat',
      shownReminderIds: new Set<string>(),

      login: async (email, password) => {
        const response = await api.post('/auth/login', { email, password })
        set({ 
          isAuthenticated: true, 
          token: response.access_token 
        })
        api.setToken(response.access_token)
        const user = await api.get('/auth/me')
        const greeting: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: "Hey there. I'm Donna — your schedule, your emails, your reminders? Consider them handled. What do you need?",
          timestamp: new Date()
        }
        set({ 
          user: { 
            email: user.email, 
            googleConnected: user.google_connected,
            microsoftConnected: user.microsoft_connected,
            slackConnected: user.slack_connected,
            onboardingComplete: user.onboarding_complete || false
          },
          messages: [greeting]
        })
      },

      register: async (email, password) => {
        const response = await api.post('/auth/register', { email, password })
        set({ 
          isAuthenticated: true, 
          token: response.access_token 
        })
        api.setToken(response.access_token)
        const user = response.user || await api.get('/auth/me')
        set({ user: { 
          email: user.email || email, 
          googleConnected: user.google_connected || false,
          microsoftConnected: user.microsoft_connected || false,
          slackConnected: user.slack_connected || false,
          onboardingComplete: user.onboarding_complete || false
        }})
      },

      loginWithToken: async (token) => {
        api.setToken(token)
        try {
          const user = await api.get('/auth/me')
          const greeting: Message = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: "Hey there. I'm Donna — your schedule, your emails, your reminders? Consider them handled. What do you need?",
            timestamp: new Date()
          }
          set({ 
            isAuthenticated: true, 
            token,
            user: { 
              email: user.email, 
              googleConnected: user.google_connected,
              microsoftConnected: user.microsoft_connected,
              slackConnected: user.slack_connected,
              onboardingComplete: user.onboarding_complete || false
            },
            messages: [greeting]
          })
        } catch (error) {
          api.setToken(null)
          throw new Error('Invalid token')
        }
      },

      logout: () => {
        set({ isAuthenticated: false, token: null, user: null, messages: [], isMiniMode: false })
        api.setToken(null)
      },

      checkAuth: async () => {
        const { token } = get()
        if (token) {
          api.setToken(token)
          try {
            const user = await api.get('/auth/me')
            set({ 
              isAuthenticated: true,
              user: {
                email: user.email,
                googleConnected: user.google_connected,
                microsoftConnected: user.microsoft_connected,
                slackConnected: user.slack_connected,
                onboardingComplete: user.onboarding_complete || false
              }
            })
          } catch (error) {
            // Token is invalid, clear it
            api.setToken(null)
            set({ isAuthenticated: false, token: null, user: null })
          }
        }
      },
      
      completeOnboarding: async () => {
        await api.post('/onboarding/complete')
        const { user } = get()
        if (user) {
          set({ 
            user: { ...user, onboardingComplete: true }
          })
        }
      },

      sendMessage: async (text) => {
        const { messages } = get()
        const userMessage: Message = {
          id: crypto.randomUUID(),
          role: 'user',
          content: text,
          timestamp: new Date()
        }
        
        set({ 
          messages: [...messages, userMessage].slice(-10),
          isLoading: true 
        })

        try {
          const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
          
          const response = await api.post('/utterance/process', {
            text,
            current_time: new Date().toISOString(),
            timezone,
            device_info: { platform: 'desktop' }
          })

          // Extract email entities if this is a draft_email intent
          let emailEntities: { to: string; subject: string; body: string } | undefined = undefined
          if (response.intent === 'draft_email' && response.entities) {
            const entities = response.entities
            const to = entities.to || entities.recipient || entities.email || ''
            const subject = entities.subject || ''
            const body = entities.body || entities.email_body || entities.message || ''
            if (to && subject !== undefined && body !== undefined) {
              emailEntities = { to, subject, body }
            }
          }

          const assistantMessage: Message = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: response.response,
            timestamp: new Date(),
            intent: response.intent,
            requiresConfirmation: response.requires_confirmation,
            actionId: response.action_id,
            emailEntities
          }

          set(state => ({ 
            messages: [...state.messages, assistantMessage].slice(-10),
            isLoading: false 
          }))
        } catch (error) {
          set({ isLoading: false })
          console.error('Failed to send message:', error)
        }
      },

      confirmAction: async (actionId, confirmed) => {
        try {
          const result = await api.post('/action/confirm', { action_id: actionId, confirmed })
          const { messages } = get()
          
          // Check if this was a reminder creation action or draft_email action
          const actionMessage = messages.find(msg => msg.actionId === actionId)
          const wasReminderAction = actionMessage?.intent === 'create_reminder'
          const wasDraftEmailAction = actionMessage?.intent === 'draft_email'
          
          // If draft_email was confirmed, preserve emailEntities for send button
          const updatedMessages = messages.map(msg => {
            if (msg.actionId === actionId) {
              // Preserve emailEntities if this was a draft_email action
              const emailEntities = wasDraftEmailAction ? msg.emailEntities : undefined
              return { ...msg, requiresConfirmation: false, actionId: undefined, emailEntities }
            }
            return msg
          })
          
          const resultMessage: Message = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: confirmed 
              ? (result.status === 'executed' ? 'Done! Action completed successfully.' : `Action failed: ${result.message}`)
              : 'Action cancelled.',
            timestamp: new Date()
          }
          
          set({ messages: [...updatedMessages, resultMessage].slice(-10) })
          
          // Refresh digest if a reminder was created
          if (confirmed && wasReminderAction && result.status === 'executed') {
            const { fetchDailyDigest } = get()
            setTimeout(() => {
              fetchDailyDigest()
            }, 500)
          }
        } catch (error) {
          console.error('Failed to confirm action:', error)
        }
      },

      sendEmail: async (to, subject, body) => {
        try {
          const result = await api.post('/email/send', {
            to,
            subject,
            body,
            provider: 'google'
          })
          
          const { messages } = get()
          const resultMessage: Message = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: result.status === 'sent' 
              ? `Email sent successfully to ${to}!`
              : `Failed to send email: ${result.message || 'Unknown error'}`,
            timestamp: new Date()
          }
          
          set({ messages: [...messages, resultMessage].slice(-10) })
        } catch (error: any) {
          const { messages } = get()
          const errorMessage: Message = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Failed to send email: ${error.message || 'Unknown error'}`,
            timestamp: new Date()
          }
          set({ messages: [...messages, errorMessage].slice(-10) })
        }
      },

      startRecording: async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
          const chunks: Blob[] = []
          
          mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) chunks.push(e.data)
          }
          
          mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(track => track.stop())
            const audioBlob = new Blob(chunks, { type: 'audio/webm' })
            
            set({ isLoading: true })
            try {
              const response = await api.uploadAudio('/utterance/voice', audioBlob)
              const { messages } = get()
              
              const assistantMessage: Message = {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: response.response,
                timestamp: new Date(),
                intent: response.intent,
                requiresConfirmation: response.requires_confirmation,
                actionId: response.action_id
              }
              
              set(state => ({
                messages: [...state.messages, assistantMessage].slice(-10),
                isLoading: false
              }))
            } catch (error) {
              console.error('Voice processing failed:', error)
              set({ isLoading: false })
            }
          }
          
          ;(window as any).__mediaRecorder = mediaRecorder
          mediaRecorder.start()
          set({ isRecording: true })
        } catch (error) {
          console.error('Failed to start recording:', error)
        }
      },
      
      stopRecording: async () => {
        const recorder = (window as any).__mediaRecorder as MediaRecorder | undefined
        if (recorder && recorder.state === 'recording') {
          recorder.stop()
        }
        set({ isRecording: false })
      },

      fetchReminders: async () => {
        const response = await api.get('/reminders/list?status=active')
        set({ reminders: response.reminders.map((r: any) => ({
          id: r.id,
          text: r.text,
          dueTime: new Date(r.due_time),
          status: r.status
        }))})
      },

      pollDueReminders: async () => {
        try {
          const response = await api.get('/reminders/due?within_minutes=1')
          const dueReminders = response.reminders
          const state = get()
          
          // Initialize Set if it doesn't exist (for persistence compatibility)
          let shownIds = state.shownReminderIds || new Set<string>()
          
          for (const reminder of dueReminders) {
            // Skip if we've already shown this reminder
            if (shownIds.has(reminder.id)) {
              continue
            }
            
            // Mark as shown
            shownIds.add(reminder.id)
            set({ shownReminderIds: new Set(shownIds) })
            
            const timestamp = new Date().toLocaleTimeString()
            console.log(`\n🔔 [REMINDER - ${timestamp}]`)
            console.log(`   ${reminder.text}`)
            // Parse UTC datetime correctly - handle Z suffix
            const dueTimeStr = typeof reminder.due_time === 'string' && reminder.due_time.endsWith('Z')
              ? reminder.due_time 
              : typeof reminder.due_time === 'string' 
                ? reminder.due_time + 'Z'
                : reminder.due_time
            console.log(`   Due: ${new Date(dueTimeStr).toLocaleString()}`)
            console.log('─'.repeat(50))
            
            // Send desktop notification using Tauri notification API
            try {
              const { sendNotification } = await import('@tauri-apps/api/notification')
              await sendNotification({
                title: '🔔 Reminder',
                body: reminder.text
              })
            } catch (notifError) {
              console.error('Failed to send notification:', notifError)
            }
          }
        } catch (error) {
          console.error('Failed to poll reminders:', error)
        }
      },

      pollUpcomingMeetings: async () => {
        try {
          const response = await api.get('/calendar/events?max_results=10')
          const events = response.events || []
          const now = new Date()
          const fifteenMinutesFromNow = new Date(now.getTime() + 15 * 60 * 1000)
          
          // Track notified events in sessionStorage to avoid duplicate notifications
          const notifiedEvents = JSON.parse(sessionStorage.getItem('notifiedEvents') || '[]')
          
          for (const event of events) {
            const startTime = new Date(event.start)
            const eventId = event.id
            
            // Check if meeting starts within 15 minutes and we haven't notified yet
            if (startTime > now && startTime <= fifteenMinutesFromNow && !notifiedEvents.includes(eventId)) {
              const minutesUntil = Math.round((startTime.getTime() - now.getTime()) / (1000 * 60))
              const eventTitle = event.summary || 'Meeting'
              
              // Send desktop notification
              try {
                const { sendNotification } = await import('@tauri-apps/api/notification')
                await sendNotification({
                  title: `📅 Meeting in ${minutesUntil} minute${minutesUntil !== 1 ? 's' : ''}`,
                  body: eventTitle
                })
                
                // Mark as notified
                notifiedEvents.push(eventId)
                sessionStorage.setItem('notifiedEvents', JSON.stringify(notifiedEvents))
              } catch (notifError) {
                console.error('Failed to send meeting notification:', notifError)
              }
            }
          }
          
          // Clean up old event IDs (older than 1 hour)
          const oneHourAgo = now.getTime() - 60 * 60 * 1000
          const cleaned = notifiedEvents.filter((id: string) => {
            const event = events.find((e: any) => e.id === id)
            if (!event) return false
            return new Date(event.start).getTime() > oneHourAgo
          })
          sessionStorage.setItem('notifiedEvents', JSON.stringify(cleaned))
        } catch (error) {
          console.error('Failed to poll upcoming meetings:', error)
        }
      },

      refreshUser: async () => {
        try {
          const user = await api.get('/auth/me')
          set({ user: { 
            email: user.email, 
            googleConnected: user.google_connected,
            microsoftConnected: user.microsoft_connected,
            slackConnected: user.slack_connected,
            onboardingComplete: user.onboarding_complete || false
          }})
        } catch (error) {
          console.error('Failed to refresh user:', error)
        }
      },

      clearMessages: () => {
        const greeting: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: "Hey there. I'm Donna — your schedule, your emails, your reminders? Consider them handled. What do you need?",
          timestamp: new Date()
        }
        set({ messages: [greeting] })
      },

      clearHistory: async () => {
        try {
          await api.post('/utterance/clear-history', {})
        } catch (error) {
          console.log('Clear history endpoint not available')
        }
        const greeting: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: "Fresh start. I like it. What's on the agenda?",
          timestamp: new Date()
        }
        set({ messages: [greeting] })
      },

      // Mini mode & widget
      toggleMiniMode: async () => {
        const { isMiniMode } = get()
        try {
          const { invoke } = await import('@tauri-apps/api/tauri')
          if (isMiniMode) {
            await invoke('exit_mini_mode')
          } else {
            await invoke('enter_mini_mode')
          }
          set({ isMiniMode: !isMiniMode })
        } catch (error) {
          console.error('Failed to toggle mini mode:', error)
          // Still toggle the state for UI update
          set({ isMiniMode: !isMiniMode })
        }
      },

      setWidgetMode: (mode) => {
        set({ widgetMode: mode })
      },

      // Todos
      addTodo: (text) => {
        const { todos } = get()
        const newTodo: TodoItem = {
          id: crypto.randomUUID(),
          text,
          completed: false,
          createdAt: new Date()
        }
        set({ todos: [...todos, newTodo] })
      },

      toggleTodo: (id) => {
        const { todos } = get()
        set({
          todos: todos.map(t => t.id === id ? { ...t, completed: !t.completed } : t)
        })
      },

      removeTodo: (id) => {
        const { todos } = get()
        set({ todos: todos.filter(t => t.id !== id) })
      },

      // Daily digest
      fetchDailyDigest: async () => {
        try {
          const response = await api.get('/digest/daily')
          set({ dailyDigest: response })
        } catch (error) {
          console.error('Failed to fetch daily digest:', error)
        }
      }
    }),
    {
      name: 'agent-storage',
      partialize: (state) => ({ 
        token: state.token,
        todos: state.todos 
      })
    }
  )
)
