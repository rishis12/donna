import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../lib/api'
import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/api/notification'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  intent?: string
  requiresConfirmation?: boolean
  actionId?: string
}

interface Reminder {
  id: string
  text: string
  dueTime: Date
  status: 'active' | 'completed' | 'cancelled'
}

interface AppState {
  isAuthenticated: boolean
  token: string | null
  user: { email: string; googleConnected: boolean; microsoftConnected: boolean } | null
  messages: Message[]
  reminders: Reminder[]
  isLoading: boolean
  isRecording: boolean
  
  // Actions
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  loginWithToken: (token: string) => Promise<void>
  logout: () => void
  checkAuth: () => void
  sendMessage: (text: string) => Promise<void>
  confirmAction: (actionId: string, confirmed: boolean) => Promise<void>
  startRecording: () => void
  stopRecording: () => Promise<void>
  fetchReminders: () => Promise<void>
  pollDueReminders: () => Promise<void>
  refreshUser: () => Promise<void>
  clearMessages: () => void
  clearHistory: () => Promise<void>
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      token: null,
      user: null,
      messages: [],
      reminders: [],
      isLoading: false,
      isRecording: false,

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
            microsoftConnected: user.microsoft_connected 
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
        set({ user: { 
          email, 
          googleConnected: false,
          microsoftConnected: false 
        }})
      },

      loginWithToken: async (token) => {
        // Verify the token by fetching user info
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
              microsoftConnected: user.microsoft_connected 
            },
            messages: [greeting]
          })
        } catch (error) {
          api.setToken(null)
          throw new Error('Invalid token')
        }
      },

      logout: () => {
        set({ isAuthenticated: false, token: null, user: null, messages: [] })
        api.setToken(null)
      },

      checkAuth: () => {
        const { token } = get()
        if (token) {
          api.setToken(token)
          set({ isAuthenticated: true })
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
          // Get timezone for proper time handling
          const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
          
          const response = await api.post('/utterance/process', {
            text,
            current_time: new Date().toISOString(),
            timezone,
            device_info: { platform: 'desktop' }
          })

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
            messages: [...state.messages, assistantMessage].slice(-5),
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
          
          // Update the message that had the confirmation buttons to remove them
          const updatedMessages = messages.map(msg => 
            msg.actionId === actionId 
              ? { ...msg, requiresConfirmation: false, actionId: undefined }
              : msg
          )
          
          // Add result message
          const resultMessage: Message = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: confirmed 
              ? (result.status === 'executed' ? 'Done! Action completed successfully.' : `Action failed: ${result.message}`)
              : 'Action cancelled.',
            timestamp: new Date()
          }
          
          set({ messages: [...updatedMessages, resultMessage].slice(-5) })
        } catch (error) {
          console.error('Failed to confirm action:', error)
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
            
            // Send to backend
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
                messages: [...state.messages, assistantMessage].slice(-5),
                isLoading: false
              }))
            } catch (error) {
              console.error('Voice processing failed:', error)
              set({ isLoading: false })
            }
          }
          
          // Store recorder reference for stopping
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
          
          // Check if Tauri notifications are available and permitted
          let permissionGranted = await isPermissionGranted()
          if (!permissionGranted) {
            const permission = await requestPermission()
            permissionGranted = permission === 'granted'
          }
          
          // Show Tauri native notifications for due reminders
          for (const reminder of dueReminders) {
            if (permissionGranted) {
              sendNotification({
                title: 'Reminder',
                body: reminder.text
              })
            }
          }
        } catch (error) {
          console.error('Failed to poll reminders:', error)
        }
      },

      refreshUser: async () => {
        try {
          const user = await api.get('/auth/me')
          set({ user: { 
            email: user.email, 
            googleConnected: user.google_connected,
            microsoftConnected: user.microsoft_connected 
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
          // Clear backend history
          await api.post('/utterance/clear-history', {})
        } catch (error) {
          // Endpoint might not exist yet, that's okay
          console.log('Clear history endpoint not available')
        }
        // Clear frontend and show greeting
        const greeting: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: "Fresh start. I like it. What's on the agenda?",
          timestamp: new Date()
        }
        set({ messages: [greeting] })
      }
    }),
    {
      name: 'agent-storage',
      partialize: (state) => ({ token: state.token })
    }
  )
)

