import { useState } from 'react'

interface LoginScreenProps {
  onLogin: (userId: string, goToIntake: boolean) => void
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [username, setUsername] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = username.trim()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    try {
      const base = `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${import.meta.env.VITE_WS_HOST || window.location.hostname}:${import.meta.env.VITE_WS_PORT || (window.location.protocol === 'https:' ? '443' : '8000')}`
      const res = await fetch(`${base}/api/users/${encodeURIComponent(trimmed)}/profile`)
      const data = await res.json()
      const isOnboarded = data?.is_onboarded === true
      onLogin(trimmed, !isOnboarded)
    } catch (err) {
      setError('Could not reach server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0D1117] flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-[#21262d] rounded-xl p-8 shadow-xl border border-[#00CFD1]/20">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[#00CFD1] mb-2">SuperSet</h1>
          <p className="text-gray-400">Your AI-powered training stack</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-2">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              className="w-full px-4 py-2 bg-[#161B22] border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#00CFD1] focus:border-transparent"
              required
              disabled={loading}
            />
          </div>

          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full px-6 py-3 bg-[#00CFD1] text-[#0D1117] font-semibold rounded-lg hover:bg-[#00e5e7] focus:outline-none focus:ring-2 focus:ring-[#00CFD1] focus:ring-offset-2 focus:ring-offset-[#0D1117] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Checking...' : 'Continue'}
          </button>
        </form>
      </div>
    </div>
  )
}
