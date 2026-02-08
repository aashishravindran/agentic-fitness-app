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
  const [maxWorkoutsPerWeek, setMaxWorkoutsPerWeek] = useState(4)
  const [showHistory, setShowHistory] = useState(false)
  const [workoutHistory, setWorkoutHistory] = useState<Array<Record<string, unknown>>>([])
  const { connectionStatus, sendMessage } = useWorkoutSocket(userId || '')
  const { state, workout, isWorkingOut, error, setError, clearState, setState } = useWorkoutStore()

  useEffect(() => {
    if (!showHistory || !userId) return
    const base = `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${import.meta.env.VITE_WS_HOST || window.location.hostname}:${import.meta.env.VITE_WS_PORT || (window.location.protocol === 'https:' ? '443' : '8000')}`
    fetch(`${base}/api/users/${userId}/history`)
      .then((res) => res.json())
      .then((data) => setWorkoutHistory(data.workout_history || []))
      .catch(() => setWorkoutHistory([]))
  }, [showHistory, userId])

  const handleLogin = (newUserId: string, goal: string) => {
    clearState()
    setUserId(newUserId)
    setUserGoal(goal)
  }

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
      max_workouts_per_week: maxWorkoutsPerWeek,
    })
    setUserInput('')
  }

  const handleLogSet = (exerciseName: string, exerciseId: string | null, weight: number, reps: number, rpe: number) => {
    const data: Record<string, unknown> = { weight, reps, rpe }
    if (exerciseId) data.exercise_id = exerciseId
    else data.exercise = exerciseName
    sendMessage({ type: 'LOG_SET', data })
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
          maxWorkouts={state?.max_workouts_per_week ?? maxWorkoutsPerWeek}
          persona={state?.selected_persona || 'iron'}
          fatigueScores={state?.fatigue_scores || {}}
          userId={userId}
          onUpdateMaxWorkouts={async (newMax: number) => {
            const base = `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${import.meta.env.VITE_WS_HOST || window.location.hostname}:${import.meta.env.VITE_WS_PORT || (window.location.protocol === 'https:' ? '443' : '8000')}`
            const res = await fetch(`${base}/api/users/${userId}/settings`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ max_workouts_per_week: newMax }),
            })
            if (res.ok) {
              const updated = await res.json()
              if (updated) setState(updated)
              setMaxWorkoutsPerWeek(newMax)
            }
          }}
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
          onViewHistory={() => setShowHistory(true)}
          onStartFresh={state ? () => {
            if (window.confirm('Start completely fresh? This will delete all your workout history and progress for this account.')) {
              sendMessage({ type: 'RESET_USER' })
            }
          } : undefined}
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
              setMaxWorkoutsPerWeek(4)
              setShowHistory(false)
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

        {/* Past workouts modal */}
        {showHistory && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowHistory(false)}>
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
              <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-semibold text-gray-800">Past workouts</h2>
                <button type="button" onClick={() => setShowHistory(false)} className="text-gray-500 hover:text-gray-700 text-xl leading-none">×</button>
              </div>
              <div className="p-4 overflow-y-auto flex-1">
                {workoutHistory.length === 0 ? (
                  <p className="text-gray-500 text-sm">No past workouts yet.</p>
                ) : (
                  <ul className="space-y-3">
                    {workoutHistory.map((w, i) => {
                      const title = (w as Record<string, string>).focus_area || (w as Record<string, string>).focus_system || (w as Record<string, string>).focus_attribute || 'Workout'
                      const exercises = (w as Record<string, unknown>).exercises as Array<Record<string, unknown>> | undefined
                      const poses = (w as Record<string, unknown>).poses as Array<Record<string, unknown>> | undefined
                      return (
                        <li key={i} className="border border-gray-200 rounded-lg p-3 text-left">
                          <div className="font-medium text-gray-800">{title}</div>
                          {Array.isArray(exercises) && exercises.length > 0 && (
                            <ul className="mt-2 text-sm text-gray-600 space-y-1">
                              {exercises.map((ex, j) => {
                                const name = (ex.exercise_name as string) || (ex.pose_name as string) || `Exercise ${j + 1}`
                                const detail = ex.sets != null && ex.reps != null
                                  ? `${ex.sets} × ${ex.reps}`
                                  : ex.work_duration != null
                                    ? String(ex.work_duration)
                                    : ex.round_duration != null
                                      ? String(ex.round_duration)
                                      : ex.duration != null
                                        ? String(ex.duration)
                                        : ''
                                return (
                                  <li key={j} className="flex justify-between gap-2">
                                    <span>{name}</span>
                                    {detail && <span className="text-gray-500">{detail}</span>}
                                  </li>
                                )
                              })}
                            </ul>
                          )}
                          {Array.isArray(poses) && poses.length > 0 && (
                            <ul className="mt-2 text-sm text-gray-600 space-y-1">
                              {poses.map((po, j) => {
                                const name = (po.pose_name as string) || `Pose ${j + 1}`
                                const detail = po.duration != null ? String(po.duration) : ''
                                return (
                                  <li key={j} className="flex justify-between gap-2">
                                    <span>{name}</span>
                                    {detail && <span className="text-gray-500">{detail}</span>}
                                  </li>
                                )
                              })}
                            </ul>
                          )}
                          {(!exercises?.length && !poses?.length) && (
                            <p className="mt-1 text-sm text-gray-500">No exercises listed</p>
                          )}
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
