import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Settings, X, Check, ExternalLink, Power, RefreshCw } from 'lucide-react'
import { open } from '@tauri-apps/api/shell'
import { invoke } from '@tauri-apps/api/tauri'
import { api } from '../lib/api'

interface SettingsPanelProps {
  isOpen: boolean
  onClose: () => void
}

export default function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const { user, refreshUser } = useAppStore()
  const [isConnecting, setIsConnecting] = useState<'google' | 'microsoft' | null>(null)
  const [autoStartEnabled, setAutoStartEnabled] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    if (isOpen) {
      invoke<boolean>('get_autostart_enabled').then(setAutoStartEnabled).catch(console.error)
      // Refresh user state when panel opens
      refreshUser()
    }
  }, [isOpen, refreshUser])

  const toggleAutoStart = async () => {
    try {
      await invoke('set_autostart_enabled', { enabled: !autoStartEnabled })
      setAutoStartEnabled(!autoStartEnabled)
    } catch (error) {
      console.error('Failed to toggle autostart:', error)
    }
  }

  const handleConnectGoogle = async () => {
    setIsConnecting('google')
    try {
      const response = await api.get('/auth/google/connect')
      await open(response.auth_url)
    } catch (error) {
      console.error('Failed to open Google auth:', error)
    } finally {
      setIsConnecting(null)
    }
  }

  const handleConnectMicrosoft = async () => {
    setIsConnecting('microsoft')
    try {
      const response = await api.get('/auth/microsoft/connect')
      await open(response.auth_url)
    } catch (error) {
      console.error('Failed to open Microsoft auth:', error)
    } finally {
      setIsConnecting(null)
    }
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refreshUser()
    setIsRefreshing(false)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface-900 border border-surface-700/50 rounded-2xl w-full max-w-md m-4 overflow-hidden animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-700/30">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-accent-500" />
            <h2 className="text-lg font-medium text-surface-100">Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-surface-200/60 hover:text-surface-100 hover:bg-surface-800/50 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Account Info */}
          <div className="p-3 bg-surface-800/50 rounded-xl">
            <p className="text-xs text-surface-200/50 uppercase tracking-wider mb-1">Account</p>
            <p className="text-surface-100 text-sm">{user?.email || 'Not logged in'}</p>
          </div>

          {/* Connected Services */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-surface-200/50 uppercase tracking-wider">Connected Services</p>
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="p-1.5 text-surface-200/40 hover:text-surface-100 hover:bg-surface-800/50 rounded-lg transition-colors"
                title="Refresh connection status"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>
            
            {/* Google */}
            <button
              onClick={handleConnectGoogle}
              disabled={isConnecting !== null}
              className="w-full flex items-center justify-between p-4 bg-surface-800/30 hover:bg-surface-800/50 border border-surface-700/30 rounded-xl mb-2 transition-all group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                </div>
                <div className="text-left">
                  <p className="text-surface-100 font-medium text-sm">Google</p>
                  <p className="text-surface-200/50 text-xs">Calendar & Gmail</p>
                </div>
              </div>
              {user?.googleConnected ? (
                <div className="flex items-center gap-1.5 text-emerald-400 text-xs">
                  <Check className="w-4 h-4" />
                  Connected
                </div>
              ) : (
                <div className="flex items-center gap-1 text-accent-400 text-xs group-hover:text-accent-300">
                  Connect
                  <ExternalLink className="w-3 h-3" />
                </div>
              )}
            </button>

            {/* Microsoft */}
            <button
              onClick={handleConnectMicrosoft}
              disabled={isConnecting !== null}
              className="w-full flex items-center justify-between p-4 bg-surface-800/30 hover:bg-surface-800/50 border border-surface-700/30 rounded-xl transition-all group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[#2F2F2F] flex items-center justify-center">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#F25022" d="M1 1h10v10H1z"/>
                    <path fill="#00A4EF" d="M1 13h10v10H1z"/>
                    <path fill="#7FBA00" d="M13 1h10v10H13z"/>
                    <path fill="#FFB900" d="M13 13h10v10H13z"/>
                  </svg>
                </div>
                <div className="text-left">
                  <p className="text-surface-100 font-medium text-sm">Microsoft 365</p>
                  <p className="text-surface-200/50 text-xs">Outlook Calendar & Mail</p>
                </div>
              </div>
              {user?.microsoftConnected ? (
                <div className="flex items-center gap-1.5 text-emerald-400 text-xs">
                  <Check className="w-4 h-4" />
                  Connected
                </div>
              ) : (
                <div className="flex items-center gap-1 text-accent-400 text-xs group-hover:text-accent-300">
                  Connect
                  <ExternalLink className="w-3 h-3" />
                </div>
              )}
            </button>
          </div>

          {/* Startup Settings */}
          <div>
            <p className="text-xs text-surface-200/50 uppercase tracking-wider mb-3">Startup</p>
            <button
              onClick={toggleAutoStart}
              className="w-full flex items-center justify-between p-4 bg-surface-800/30 hover:bg-surface-800/50 border border-surface-700/30 rounded-xl transition-all"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-surface-700/50 flex items-center justify-center">
                  <Power className="w-5 h-5 text-surface-200" />
                </div>
                <div className="text-left">
                  <p className="text-surface-100 font-medium text-sm">Launch at startup</p>
                  <p className="text-surface-200/50 text-xs">Start Agent when you log in</p>
                </div>
              </div>
              <div className={`w-11 h-6 rounded-full transition-colors ${autoStartEnabled ? 'bg-accent-500' : 'bg-surface-700'} relative`}>
                <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${autoStartEnabled ? 'left-6' : 'left-1'}`} />
              </div>
            </button>
          </div>

          {/* Info */}
          <p className="text-xs text-surface-200/40 text-center">
            Connect your accounts to let the agent manage your calendar and emails.
          </p>
        </div>
      </div>
    </div>
  )
}

