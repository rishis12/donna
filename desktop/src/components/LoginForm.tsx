import { useState } from 'react'
import { useAppStore } from '../stores/appStore'
import { Mail, Lock, ArrowRight, Clipboard } from 'lucide-react'
import { open } from '@tauri-apps/api/shell'
import { api } from '../lib/api'

export default function LoginForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showEmailForm, setShowEmailForm] = useState(false)
  const [isRegistering, setIsRegistering] = useState(false)
  const [error, setError] = useState('')
  const [showTokenInput, setShowTokenInput] = useState(false)
  const [token, setToken] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login, register, loginWithToken } = useAppStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      if (isRegistering) {
        await register(email, password)
      } else {
        await login(email, password)
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleSignIn = async () => {
    setError('')
    setIsLoading(true)
    try {
      const response = await api.get('/auth/google')
      await open(response.auth_url)
      setShowTokenInput(true)
    } catch (err: any) {
      setError('Failed to start Google sign-in')
    } finally {
      setIsLoading(false)
    }
  }

  const handleMicrosoftSignIn = async () => {
    setError('')
    setIsLoading(true)
    try {
      const response = await api.get('/auth/microsoft')
      await open(response.auth_url)
      setShowTokenInput(true)
    } catch (err: any) {
      setError('Failed to start Microsoft sign-in')
    } finally {
      setIsLoading(false)
    }
  }

  const handleTokenSubmit = async () => {
    if (!token.trim()) return
    setError('')
    setIsLoading(true)
    try {
      await loginWithToken(token.trim())
    } catch (err: any) {
      setError('Invalid token. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePasteToken = async () => {
    try {
      const text = await navigator.clipboard.readText()
      setToken(text)
    } catch (err) {
      // Clipboard access may be denied
    }
  }

  // Token input view
  if (showTokenInput) {
    return (
      <div className="w-full max-w-md animate-fade-in">
        <div className="bg-white rounded-3xl p-8 shadow-xl shadow-surface-300/30 border border-surface-200">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-success-400/20 mb-4">
              <Clipboard className="w-8 h-8 text-success-400" />
            </div>
            <h1 className="text-2xl font-semibold text-surface-800">Almost there!</h1>
            <p className="text-surface-500 text-sm mt-2 leading-relaxed">
              Copy the token from your browser and paste it below.
            </p>
          </div>

          <div className="space-y-4">
            <textarea
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste your token here..."
              rows={3}
              className="w-full bg-surface-50 border border-surface-200 rounded-2xl py-3 px-4 text-surface-800 placeholder:text-surface-400 focus:outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all resize-none text-sm"
            />

            <button
              type="button"
              onClick={handlePasteToken}
              className="w-full bg-surface-50 hover:bg-surface-100 border border-surface-200 text-surface-600 py-3 rounded-2xl flex items-center justify-center gap-2 transition-all font-medium"
            >
              <Clipboard className="w-4 h-4" />
              Paste from Clipboard
            </button>

            {error && (
              <p className="text-error-400 text-sm text-center">{error}</p>
            )}

            <button
              type="button"
              onClick={handleTokenSubmit}
              disabled={!token.trim() || isLoading}
              className="w-full bg-primary-400 hover:bg-primary-500 disabled:bg-surface-200 text-white disabled:text-surface-400 font-medium py-3.5 rounded-2xl flex items-center justify-center gap-2 transition-all"
            >
              {isLoading ? 'Verifying...' : 'Continue'}
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              type="button"
              onClick={() => {
                setShowTokenInput(false)
                setToken('')
                setError('')
              }}
              className="w-full text-surface-500 hover:text-surface-700 text-sm py-2 transition-colors"
            >
              Go back
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Email/password form view
  if (showEmailForm) {
    return (
      <div className="w-full max-w-md animate-fade-in">
        <div className="bg-white rounded-3xl p-8 shadow-xl shadow-surface-300/30 border border-surface-200">
          <div className="text-center mb-6">
            <div className="text-5xl mb-4">👋</div>
            <h1 className="text-2xl font-semibold text-surface-800">Welcome to Donna</h1>
            <p className="text-surface-500 text-sm mt-1">Your friendly assistant</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                className="w-full bg-surface-50 border border-surface-200 rounded-2xl py-3.5 pl-11 pr-4 text-surface-800 placeholder:text-surface-400 focus:outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all"
                required
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="w-full bg-surface-50 border border-surface-200 rounded-2xl py-3.5 pl-11 pr-4 text-surface-800 placeholder:text-surface-400 focus:outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all"
                required
              />
            </div>

            {error && (
              <p className="text-error-400 text-sm text-center">{error}</p>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary-400 hover:bg-primary-500 text-white font-medium py-3.5 rounded-2xl flex items-center justify-center gap-2 transition-all"
            >
              {isLoading ? 'Please wait...' : (isRegistering ? 'Create Account' : 'Sign In')}
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              type="button"
              onClick={() => setIsRegistering(!isRegistering)}
              className="w-full text-surface-500 hover:text-surface-700 text-sm py-2 transition-colors"
            >
              {isRegistering ? 'Already have an account? Sign in' : "Don't have an account? Register"}
            </button>

            <button
              type="button"
              onClick={() => {
                setShowEmailForm(false)
                setError('')
              }}
              className="w-full text-surface-400 hover:text-surface-500 text-sm py-1 transition-colors"
            >
              Back to social login
            </button>
          </form>
        </div>
      </div>
    )
  }

  // Main social login view
  return (
    <div className="w-full max-w-md animate-fade-in">
      <div className="bg-white rounded-3xl p-8 shadow-xl shadow-surface-300/30 border border-surface-200">
        <div className="text-center mb-6">
          <div className="text-5xl mb-4">👋</div>
          <h1 className="text-2xl font-semibold text-surface-800">Welcome to Donna</h1>
          <p className="text-surface-500 text-sm mt-1">Your friendly assistant</p>
        </div>

        <div className="space-y-3">
          {/* Google Sign In */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={isLoading}
            className="w-full bg-white hover:bg-surface-50 border border-surface-200 text-surface-700 font-medium py-3.5 rounded-2xl flex items-center justify-center gap-3 transition-all"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
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
            Continue with Google
          </button>

          {/* Microsoft Sign In */}
          <button
            type="button"
            onClick={handleMicrosoftSignIn}
            disabled={isLoading}
            className="w-full bg-white hover:bg-surface-50 border border-surface-200 text-surface-700 font-medium py-3.5 rounded-2xl flex items-center justify-center gap-3 transition-all"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#F25022" d="M1 1h10v10H1z" />
              <path fill="#00A4EF" d="M1 13h10v10H1z" />
              <path fill="#7FBA00" d="M13 1h10v10H13z" />
              <path fill="#FFB900" d="M13 13h10v10H13z" />
            </svg>
            Continue with Microsoft
          </button>

          {error && (
            <p className="text-error-400 text-sm text-center pt-2">{error}</p>
          )}

          {/* Divider */}
          <div className="relative py-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-surface-200"></div>
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-4 text-surface-400 bg-white">or</span>
            </div>
          </div>

          {/* Email option */}
          <button
            type="button"
            onClick={() => setShowEmailForm(true)}
            className="w-full bg-surface-50 hover:bg-surface-100 border border-surface-200 text-surface-600 py-3.5 rounded-2xl flex items-center justify-center gap-2 transition-all font-medium"
          >
            <Mail className="w-4 h-4" />
            Continue with Email
          </button>
        </div>

        <p className="text-surface-400 text-xs text-center mt-6 leading-relaxed">
          By continuing, you agree to grant Donna access<br />
          to your calendar and email.
        </p>
      </div>
    </div>
  )
}
