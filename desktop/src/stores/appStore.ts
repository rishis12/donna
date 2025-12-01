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
  logout: () => void
  checkAuth: () => void
  sendMessage: (text: string) => Promise<void>
  confirmAction: (actionId: string, confirmed: boolean) => Promise<void>
  startRecording: () => void
  stopRecording: () => Promise<void>
  fetchReminders: () => Promise<void>
  pollDueReminders: () => Promise<void>
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
        set({ user: { 
          email: user.email, 
          googleConnected: user.google_connected,
          microsoftConnected: user.microsoft_connected 
        }})
      },

      register: async (email, password) => {
        const response = await api.post('/auth/register', { email, password })
        set({ 
          isAuthenticated: true, 
          token: response.access_token 
        })
        api.setToken(response.access_token)
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
          messages: [...messages, userMessage].slice(-5),
          isLoading: true 
        })

        try {
          const response = await api.post('/utterance/process', {
            text,
            current_time: new Date().toISOString(),
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
        await api.post('/action/confirm', { action_id: actionId, confirmed })
      },

      startRecording: () => set({ isRecording: true }),
      
      stopRecording: async () => {
        set({ isRecording: false })
        // Audio handling will be implemented with Tauri
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
          
          // Show notifications for due reminders
          for (const reminder of dueReminders) {
            if ('Notification' in window && Notification.permission === 'granted') {
              new Notification('Reminder', { body: reminder.text })
            }
          }
        } catch (error) {
          console.error('Failed to poll reminders:', error)
        }
      }
    }),
    {
      name: 'agent-storage',
      partialize: (state) => ({ token: state.token })
    }
  )
)

