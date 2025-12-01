import { useState } from 'react'
import { useAppStore } from '../stores/appStore'
import { Cpu, Mail, Lock, ArrowRight } from 'lucide-react'

export default function LoginForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isRegistering, setIsRegistering] = useState(false)
  const [error, setError] = useState('')
  const { login, register } = useAppStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      if (isRegistering) {
        await register(email, password)
      } else {
        await login(email, password)
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed')
    }
  }

  return (
    <div className="w-full max-w-md animate-fade-in">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-500 to-accent-600 mb-4 glow-effect">
          <Cpu className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-2xl font-semibold text-surface-50 tracking-tight">Agent</h1>
        <p className="text-surface-200/60 text-sm mt-1">Your AI desktop assistant</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-200/40" />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            className="w-full bg-surface-800/50 border border-surface-700/50 rounded-xl py-3 pl-11 pr-4 text-surface-100 placeholder:text-surface-200/30 focus:outline-none focus:border-accent-500/50 focus:ring-1 focus:ring-accent-500/20 transition-all"
            required
          />
        </div>

        <div className="relative">
          <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-200/40" />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full bg-surface-800/50 border border-surface-700/50 rounded-xl py-3 pl-11 pr-4 text-surface-100 placeholder:text-surface-200/30 focus:outline-none focus:border-accent-500/50 focus:ring-1 focus:ring-accent-500/20 transition-all"
            required
          />
        </div>

        {error && (
          <p className="text-red-400 text-sm text-center">{error}</p>
        )}

        <button
          type="submit"
          className="w-full bg-gradient-to-r from-accent-500 to-accent-600 hover:from-accent-400 hover:to-accent-500 text-white font-medium py-3 rounded-xl flex items-center justify-center gap-2 transition-all duration-200 hover:shadow-lg hover:shadow-accent-500/25"
        >
          {isRegistering ? 'Create Account' : 'Sign In'}
          <ArrowRight className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() => setIsRegistering(!isRegistering)}
          className="w-full text-surface-200/60 hover:text-surface-100 text-sm py-2 transition-colors"
        >
          {isRegistering ? 'Already have an account? Sign in' : "Don't have an account? Register"}
        </button>
      </form>
    </div>
  )
}

