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
  slackConnected: boolean;
}

interface CalendarEvent {
  id: string;
  summary: string;
  start: string;
  end: string;
  attendees?: string[];
}

interface TodoItem {
  id: string;
  text: string;
  completed: boolean;
  createdAt: Date;
}

interface DailyDigest {
  meetings: CalendarEvent[];
  reminders: { id: string; text: string; dueTime: string }[];
  unreadEmails: number;
}

interface AppState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  messages: Message[];
  events: CalendarEvent[];
  todos: TodoItem[];
  dailyDigest: DailyDigest | null;

  // Actions
  init: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  loginWithToken: (token: string) => Promise<void>;
  refreshUser: () => Promise<void>;
  logout: () => void;
  sendMessage: (text: string) => Promise<void>;
  confirmAction: (actionId: string, confirmed: boolean) => Promise<void>;
  fetchEvents: () => Promise<void>;
  clearHistory: () => Promise<void>;
  // Todo actions
  addTodo: (text: string) => void;
  toggleTodo: (id: string) => void;
  removeTodo: (id: string) => void;
  // Daily digest
  fetchDailyDigest: () => Promise<void>;
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
  todos: [],
  dailyDigest: null,

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
            slackConnected: user.slack_connected,
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
      user: { email, googleConnected: false, microsoftConnected: false, slackConnected: false },
      messages: [createGreeting()],
    });
  },

  loginWithToken: async (token) => {
    api.setToken(token);
    try {
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
    } catch (error) {
      api.setToken(null);
      throw error;
    }
  },

  refreshUser: async () => {
    try {
      const user = await api.get('/auth/me');
      set({
        user: {
          email: user.email,
          googleConnected: user.google_connected,
          microsoftConnected: user.microsoft_connected,
        },
      });
    } catch (error) {
      console.error('Failed to refresh user:', error);
    }
  },

  logout: () => {
    api.setToken(null);
    set({
      isAuthenticated: false,
      user: null,
      messages: [],
      events: [],
      todos: [],
      dailyDigest: null,
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
      const { messages, fetchDailyDigest } = get();

      // Check if this was a reminder creation action
      const actionMessage = messages.find(msg => msg.actionId === actionId);
      const wasReminderAction = actionMessage?.intent === 'create_reminder';

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

      // Refresh digest if a reminder was created
      if (confirmed && wasReminderAction && result.status === 'executed') {
        setTimeout(() => {
          fetchDailyDigest();
        }, 500);
      }
    } catch (error: any) {
      console.error('Confirm action failed:', error);
    }
  },

  fetchEvents: async () => {
    try {
      // Fetch a week's worth of events
      const response = await api.get('/calendar/events?max_results=50');
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

  // Todo actions - stored locally
  addTodo: (text) => {
    const { todos } = get();
    const newTodo: TodoItem = {
      id: Date.now().toString(),
      text,
      completed: false,
      createdAt: new Date(),
    };
    set({ todos: [...todos, newTodo] });
  },

  toggleTodo: (id) => {
    const { todos } = get();
    set({
      todos: todos.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t)),
    });
  },

  removeTodo: (id) => {
    const { todos } = get();
    set({ todos: todos.filter((t) => t.id !== id) });
  },

  fetchDailyDigest: async () => {
    try {
      const response = await api.get('/digest/daily');
      set({ dailyDigest: response });
    } catch (error) {
      console.log('Failed to fetch daily digest:', error);
    }
  },
}));
