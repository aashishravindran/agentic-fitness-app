import { useState } from 'react'

interface LoginScreenProps {
  onLogin: (userId: string, goal: string) => void
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [userId, setUserId] = useState('')
  const [goal, setGoal] = useState('Build strength and improve fitness')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (userId.trim()) {
      onLogin(userId.trim(), goal.trim() || 'Build strength and improve fitness')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Agentic Fitness</h1>
          <p className="text-gray-600">Your AI-powered workout coach</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="userId" className="block text-sm font-medium text-gray-700 mb-2">
              User ID
            </label>
            <input
              id="userId"
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="Enter your user ID (e.g., john_doe)"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              This ID will be used to track your progress and workout history
            </p>
          </div>

          <div>
            <label htmlFor="goal" className="block text-sm font-medium text-gray-700 mb-2">
              Fitness Goal
            </label>
            <textarea
              id="goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Build strength and improve fitness"
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Describe your fitness goals (optional)
            </p>
          </div>

          <button
            type="submit"
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-md font-semibold hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
          >
            Start Workout Session
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            Your workout history and progress will be saved automatically
          </p>
        </div>
      </div>
    </div>
  )
}
