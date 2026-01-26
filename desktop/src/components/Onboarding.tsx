import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Check, Mail, ArrowRight, Loader } from 'lucide-react'
import { open } from '@tauri-apps/api/shell'
import { api } from '../lib/api'

export default function Onboarding() {
  const { user, refreshUser, completeOnboarding } = useAppStore()
  const [isConnecting, setIsConnecting] = useState<'google' | 'slack' | 'email' | null>(null)
  const [error, setError] = useState('')

  const googleConnected = user?.googleConnected || false
  const slackConnected = user?.slackConnected || false
  // Email connection status could be based on google or microsoft
  const emailConnected = user?.googleConnected || user?.microsoftConnected || false

  const handleConnectGoogle = async () => {
    setError('')
    setIsConnecting('google')
    try {
      const response = await api.get('/auth/google/connect')
      await open(response.auth_url)
      // Refresh user after a short delay to check connection status
      setTimeout(() => {
        refreshUser()
        setIsConnecting(null)
      }, 2000)
    } catch (err: any) {
      setError('Failed to connect Google')
      setIsConnecting(null)
    }
  }

  const handleConnectSlack = async () => {
    setError('')
    setIsConnecting('slack')
    try {
      const response = await api.get('/auth/slack/connect')
      await open(response.auth_url)
      setTimeout(() => {
        refreshUser()
        setIsConnecting(null)
      }, 2000)
    } catch (err: any) {
      setError('Failed to connect Slack')
      setIsConnecting(null)
    }
  }

  const handleContinue = async () => {
    try {
      await completeOnboarding()
    } catch (err: any) {
      setError('Failed to complete onboarding')
    }
  }

  const allConnected = googleConnected && slackConnected && emailConnected

  return (
    <div className="w-full max-w-2xl animate-fade-in">
      <div className="bg-white rounded-3xl p-8 shadow-xl shadow-surface-300/30 border border-surface-200">
        <div className="text-center mb-8">
          <div className="text-5xl mb-4">👋</div>
          <h1 className="text-3xl font-semibold text-surface-800 mb-2">Welcome to Donna</h1>
          <p className="text-surface-500">Let's connect your services to get started</p>
        </div>

        <div className="space-y-4 mb-8">
          {/* Google Connection */}
          <div className={`flex items-center justify-between p-4 rounded-2xl border-2 ${
            googleConnected 
              ? 'bg-success-50 border-success-200' 
              : 'bg-surface-50 border-surface-200'
          }`}>
            <div className="flex items-center gap-4">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                googleConnected ? 'bg-success-400' : 'bg-surface-200'
              }`}>
                {googleConnected ? (
                  <Check className="w-5 h-5 text-white" />
                ) : (
                  <svg className="w-5 h-5 text-surface-400" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                )}
              </div>
              <div>
                <div className="font-medium text-surface-800">Connect Google</div>
                <div className="text-sm text-surface-500">Calendar and Gmail</div>
              </div>
            </div>
            {!googleConnected && (
              <button
                onClick={handleConnectGoogle}
                disabled={isConnecting === 'google'}
                className="px-4 py-2 bg-primary-400 hover:bg-primary-500 text-white rounded-xl text-sm font-medium disabled:opacity-50 flex items-center gap-2"
              >
                {isConnecting === 'google' ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  'Connect'
                )}
              </button>
            )}
          </div>

          {/* Slack Connection */}
          <div className={`flex items-center justify-between p-4 rounded-2xl border-2 ${
            slackConnected 
              ? 'bg-success-50 border-success-200' 
              : 'bg-surface-50 border-surface-200'
          }`}>
            <div className="flex items-center gap-4">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                slackConnected ? 'bg-success-400' : 'bg-surface-200'
              }`}>
                {slackConnected ? (
                  <Check className="w-5 h-5 text-white" />
                ) : (
                  <svg className="w-5 h-5 text-surface-400" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 5.042a2.528 2.528 0 0 1-2.52-2.52A2.528 2.528 0 0 1 18.956 0a2.528 2.528 0 0 1 2.522 2.522v2.52h-2.522zM18.956 6.313a2.528 2.528 0 0 1 2.522 2.521 2.528 2.528 0 0 1-2.522 2.521h-6.313A2.528 2.528 0 0 1 10.121 8.834a2.528 2.528 0 0 1 2.522-2.521h6.313zM15.165 18.956a2.528 2.528 0 0 1 2.521 2.522A2.528 2.528 0 0 1 15.165 24a2.528 2.528 0 0 1-2.52-2.522v-2.521h2.52zM13.894 18.956a2.528 2.528 0 0 1-2.522-2.521 2.528 2.528 0 0 1 2.522-2.521h6.313A2.528 2.528 0 0 1 24 16.435a2.528 2.528 0 0 1-2.522 2.521h-6.313z"/>
                  </svg>
                )}
              </div>
              <div>
                <div className="font-medium text-surface-800">Connect Slack</div>
                <div className="text-sm text-surface-500">Team communication</div>
              </div>
            </div>
            {!slackConnected && (
              <button
                onClick={handleConnectSlack}
                disabled={isConnecting === 'slack'}
                className="px-4 py-2 bg-primary-400 hover:bg-primary-500 text-white rounded-xl text-sm font-medium disabled:opacity-50 flex items-center gap-2"
              >
                {isConnecting === 'slack' ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  'Connect'
                )}
              </button>
            )}
          </div>

          {/* Email Connection (Google or Microsoft) */}
          <div className={`flex items-center justify-between p-4 rounded-2xl border-2 ${
            emailConnected 
              ? 'bg-success-50 border-success-200' 
              : 'bg-surface-50 border-surface-200'
          }`}>
            <div className="flex items-center gap-4">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                emailConnected ? 'bg-success-400' : 'bg-surface-200'
              }`}>
                {emailConnected ? (
                  <Check className="w-5 h-5 text-white" />
                ) : (
                  <Mail className="w-5 h-5 text-surface-400" />
                )}
              </div>
              <div>
                <div className="font-medium text-surface-800">Connect Email</div>
                <div className="text-sm text-surface-500">Gmail or Outlook</div>
              </div>
            </div>
            {emailConnected && (
              <span className="text-sm text-success-600 font-medium">Connected via {user?.googleConnected ? 'Google' : 'Microsoft'}</span>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-error-50 border border-error-200 rounded-xl text-error-600 text-sm text-center">
            {error}
          </div>
        )}

        <button
          onClick={handleContinue}
          className="w-full bg-primary-400 hover:bg-primary-500 text-white font-medium py-3.5 rounded-2xl flex items-center justify-center gap-2 transition-all"
        >
          {googleConnected || slackConnected ? 'Continue' : 'Skip for now'}
          <ArrowRight className="w-4 h-4" />
        </button>

        <p className="text-surface-400 text-xs text-center mt-4">
          {googleConnected || slackConnected
            ? 'You can connect additional services later in Settings'
            : 'Connect at least one service to get the most out of Donna, or skip and set up later'}
        </p>
      </div>
    </div>
  )
}
