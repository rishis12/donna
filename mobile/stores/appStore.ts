import { create } from 'zustand';
import { api } from '../lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  intent?: string;
  requiresConfirmation?: boolean;
  actionId?: string;
}

interface User {
  email: string;
  googleConnected: boolean;
  microsoftConnected: boolean;
}

interface CalendarEvent {
  id: string;
  summary: string;
  start: string;
  end: string;
  attendees?: string[];
}

interface AppState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  messages: Message[];
  events: CalendarEvent[];

  // Actions
  init: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  sendMessage: (text: string) => Promise<void>;
  confirmAction: (actionId: string, confirmed: boolean) => Promise<void>;
  fetchEvents: () => Promise<void>;
  clearHistory: () => Promise<void>;
}

const createGreeting = (): Message => ({
  id: Date.now().toString(),
  role: 'assistant',
  content: "Hey there! I'm Donna — your schedule, emails, and reminders? Consider them handled. What do you need?",
  timestamp: new Date(),
});

export const useAppStore = create<AppState>((set, get) => ({
  isAuthenticated: false,
  isLoading: true,
  user: null,
  messages: [],
  events: [],

  init: async () => {
    try {
      await api.init();
      if (api.getToken()) {
        const user = await api.get('/auth/me');
        set({
          isAuthenticated: true,
          user: {
            email: user.email,
            googleConnected: user.google_connected,
            microsoftConnected: user.microsoft_connected,
          },
          messages: [createGreeting()],
          isLoading: false,
        });
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      api.setToken(null);
      set({ isLoading: false });
    }
  },

  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    api.setToken(response.access_token);
    const user = await api.get('/auth/me');
    set({
      isAuthenticated: true,
      user: {
        email: user.email,
        googleConnected: user.google_connected,
        microsoftConnected: user.microsoft_connected,
      },
      messages: [createGreeting()],
    });
  },

  register: async (email, password) => {
    const response = await api.post('/auth/register', { email, password });
    api.setToken(response.access_token);
    set({
      isAuthenticated: true,
      user: { email, googleConnected: false, microsoftConnected: false },
      messages: [createGreeting()],
    });
  },

  logout: () => {
    api.setToken(null);
    set({
      isAuthenticated: false,
      user: null,
      messages: [],
      events: [],
    });
  },

  sendMessage: async (text) => {
    const { messages } = get();
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    set({ messages: [...messages, userMessage].slice(-20), isLoading: true });

    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const response = await api.post('/utterance/process', {
        text,
        current_time: new Date().toISOString(),
        timezone,
        device_info: { platform: 'mobile' },
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        intent: response.intent,
        requiresConfirmation: response.requires_confirmation,
        actionId: response.action_id,
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage].slice(-20),
        isLoading: false,
      }));
    } catch (error: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: error.message || 'Something went wrong. Try again?',
        timestamp: new Date(),
      };
      set((state) => ({
        messages: [...state.messages, errorMessage],
        isLoading: false,
      }));
    }
  },

  confirmAction: async (actionId, confirmed) => {
    try {
      const result = await api.post('/action/confirm', { action_id: actionId, confirmed });
      const { messages } = get();

      const updatedMessages = messages.map((msg) =>
        msg.actionId === actionId ? { ...msg, requiresConfirmation: false, actionId: undefined } : msg
      );

      const resultMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: confirmed
          ? result.status === 'executed'
            ? 'Done! ✓'
            : `Failed: ${result.message}`
          : 'Cancelled.',
        timestamp: new Date(),
      };

      set({ messages: [...updatedMessages, resultMessage].slice(-20) });
    } catch (error: any) {
      console.error('Confirm action failed:', error);
    }
  },

  fetchEvents: async () => {
    try {
      const response = await api.get('/calendar/events');
      set({ events: response.events || [] });
    } catch (error) {
      console.log('Failed to fetch events:', error);
    }
  },

  clearHistory: async () => {
    try {
      await api.post('/utterance/clear-history', {});
    } catch (error) {
      console.log('Clear history not available');
    }
    set({ messages: [createGreeting()] });
  },
}));


