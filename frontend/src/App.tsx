import { useState, useEffect } from 'react'
import StatusBanner from './components/StatusBanner'
import WorkoutCard from './components/WorkoutCard'
import LoginScreen from './components/LoginScreen'
import NudgeBanner from './components/NudgeBanner'
import { useWorkoutSocket } from './hooks/useWorkoutSocket'
import { useWorkoutStore } from './store/workoutStore'

function App() {
  const [userInput, setUserInput] = useState('')
  const [persona, setPersona] = useState<'iron' | 'yoga' | 'hiit' | 'kickboxing'>('iron')
  const [userId, setUserId] = useState<string | null>(null)
  const [userGoal, setUserGoal] = useState<string>('Build strength and improve fitness')
  const { connectionStatus, sendMessage } = useWorkoutSocket(userId || '')
  const { state, workout, isWorkingOut, error, setError, clearState } = useWorkoutStore()

  const [shouldReset, setShouldReset] = useState(false)

  const handleLogin = (newUserId: string, goal: string, startFresh: boolean) => {
    // Clear old state when logging in
    clearState()
    setUserId(newUserId)
    setUserGoal(goal)
    setShouldReset(startFresh)
  }

  // Reset user when connected and reset flag is set
  useEffect(() => {
    if (connectionStatus === 'connected' && shouldReset) {
      sendMessage({ type: 'RESET_USER' })
      setShouldReset(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectionStatus, shouldReset])

  // Show login screen if not logged in
  if (!userId) {
    return <LoginScreen onLogin={handleLogin} />
  }

  const handleSendInput = () => {
    if (!userInput.trim()) return
    
    sendMessage({
      type: 'USER_INPUT',
      content: userInput,
      persona: persona,
      goal: userGoal,
    })
    setUserInput('')
  }

  const handleLogSet = (exerciseName: string, weight: number, reps: number, rpe: number) => {
    sendMessage({
      type: 'LOG_SET',
      data: {
        exercise: exerciseName,
        weight: weight,
        reps: reps,
        rpe: rpe,
      },
    })
  }

  const handleFinishWorkout = () => {
    sendMessage({
      type: 'FINISH_WORKOUT',
    })
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100">
      <div className="container mx-auto px-4 py-6 max-w-4xl">
        {/* Status Banner */}
        <StatusBanner
          workoutsCompleted={state?.workouts_completed_this_week || 0}
          maxWorkouts={state?.max_workouts_per_week || 4}
          persona={state?.selected_persona || 'iron'}
          fatigueScores={state?.fatigue_scores || {}}
          onResetFatigue={() => {
            if (window.confirm(`Reset all fatigue scores to zero for ${userId}? This will clear your current fatigue levels.`)) {
              sendMessage({ type: 'RESET_FATIGUE' })
            }
          }}
          onResetWorkouts={() => {
            if (window.confirm(`Reset workouts completed counter to zero for ${userId}? This will reset your weekly progress.`)) {
              sendMessage({ type: 'RESET_WORKOUTS' })
            }
          }}
        />

        {/* Connection Status */}
        <div className="mb-4 p-3 rounded-lg bg-white shadow-sm">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${
              connectionStatus === 'connected' ? 'bg-green-500' :
              connectionStatus === 'connecting' ? 'bg-yellow-500' :
              'bg-red-500'
            }`} />
            <span className="text-sm text-gray-600">
              {connectionStatus === 'connected' ? 'Connected' :
               connectionStatus === 'connecting' ? 'Connecting...' :
               'Disconnected'}
            </span>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-red-800 mb-1">Error</h3>
                <p className="text-sm text-red-700">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-red-600 hover:text-red-800"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Nudge Banner (if agent suggests something) */}
        {state?.messages && state.messages.length > 0 && (
          <NudgeBanner
            message={state.messages[state.messages.length - 1]?.content || ''}
            onApprove={() => sendMessage({ type: 'APPROVE_SUGGESTION', approved: true })}
            onIgnore={() => sendMessage({ type: 'APPROVE_SUGGESTION', approved: false })}
          />
        )}

        {/* User Info */}
        <div className="mb-4 p-3 bg-white rounded-lg shadow-sm flex items-center justify-between">
          <div>
            <span className="text-sm text-gray-600">Logged in as: </span>
            <span className="font-semibold text-gray-800">{userId}</span>
          </div>
          <button
            onClick={() => {
              // Clear state immediately when switching users
              clearState()
              // Reset all local state
              setUserInput('')
              setPersona('iron')
              setUserGoal('Build strength and improve fitness')
              setShouldReset(false)
              // Set userId to null last to trigger WebSocket disconnect and state clearing
              setUserId(null)
            }}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Switch User
          </button>
        </div>

        {/* User Input */}
        <div className="mb-6 p-4 bg-white rounded-lg shadow-md">
          <div className="flex gap-2 mb-2">
            <select
              value={persona}
              onChange={(e) => setPersona(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="iron">Iron</option>
              <option value="yoga">Yoga</option>
              <option value="hiit">HIIT</option>
              <option value="kickboxing">Kickboxing</option>
            </select>
            <input
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendInput()}
              placeholder="Type your request (e.g., 'Start leg day')"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleSendInput}
              disabled={connectionStatus !== 'connected' || !userInput.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
          <div className="mt-2 pt-2 border-t border-gray-200">
            <button
              onClick={() => {
                if (window.confirm('Log a rest day? This will reduce your fatigue scores by 30% to simulate recovery.')) {
                  sendMessage({ type: 'LOG_REST' })
                }
              }}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
              disabled={connectionStatus !== 'connected'}
            >
              🛌 Log Rest Day
            </button>
          </div>
        </div>

        {/* Workout Card */}
        {workout && (
          <WorkoutCard
            workout={workout}
            isWorkingOut={isWorkingOut || false}
            onLogSet={handleLogSet}
            onFinishWorkout={handleFinishWorkout}
          />
        )}

        {/* Empty State */}
        {!workout && connectionStatus === 'connected' && (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">No active workout</p>
            <p className="text-sm mt-2">Send a message above to start a workout session</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
