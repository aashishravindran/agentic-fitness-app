import { useState, useEffect } from 'react'
import StatusBanner from './components/StatusBanner'
import WorkoutCard from './components/WorkoutCard'
import LoginScreen from './components/LoginScreen'
import IntakePage from './components/IntakePage'
import NudgeBanner from './components/NudgeBanner'
import Navbar from './components/Navbar'
import MaxMascot from './components/MaxMascot'
import GreetingBanner from './components/GreetingBanner'
import { useWorkoutSocket } from './hooks/useWorkoutSocket'
import { useWorkoutStore } from './store/workoutStore'

function App() {
  const [userInput, setUserInput] = useState('')
  const [userId, setUserId] = useState<string | null>(null)
  const [showIntake, setShowIntake] = useState(false)
  const [userGoal, setUserGoal] = useState<string>('Build strength and improve fitness')
  const [maxWorkoutsPerWeek, setMaxWorkoutsPerWeek] = useState(4)
  const [showQuestInput, setShowQuestInput] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [workoutHistory, setWorkoutHistory] = useState<Array<Record<string, unknown>>>([])
  const { connectionStatus, sendMessage } = useWorkoutSocket(userId || '')
  const { state, workout, isWorkingOut, greetingMessage, error, setError, clearState, setState } = useWorkoutStore()
  const [greetingComplete, setGreetingComplete] = useState(false)

  useEffect(() => {
    if (!showHistory || !userId) return
    const base = `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${import.meta.env.VITE_WS_HOST || window.location.hostname}:${import.meta.env.VITE_WS_PORT || (window.location.protocol === 'https:' ? '443' : '8000')}`
    fetch(`${base}/api/users/${userId}/history`)
      .then((res) => res.json())
      .then((data) => setWorkoutHistory(data.workout_history || []))
      .catch(() => setWorkoutHistory([]))
  }, [showHistory, userId])

  const handleLogin = (newUserId: string, goToIntake: boolean) => {
    clearState()
    setGreetingComplete(false)
    setUserId(newUserId)
    setShowIntake(goToIntake)
  }

  const showActionButtons = greetingComplete || !greetingMessage

  // Show login screen if not logged in
  if (!userId) {
    return <LoginScreen onLogin={handleLogin} />
  }

  // Show intake for new users
  if (showIntake) {
    return <IntakePage userId={userId} onComplete={() => setShowIntake(false)} />
  }

  const handleTrustMax = () => {
    sendMessage({
      type: 'USER_INPUT',
      content: 'I want a workout.',
      goal: userGoal,
      max_workouts_per_week: maxWorkoutsPerWeek,
    })
  }

  const handleSendInput = (content?: string) => {
    const text = content ?? userInput.trim()
    if (!text) return
    sendMessage({
      type: 'USER_INPUT',
      content: text,
      goal: userGoal,
      max_workouts_per_week: maxWorkoutsPerWeek,
    })
    setUserInput('')
    setShowQuestInput(false)
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
    <div className="min-h-screen bg-[#0D1117]">
      {/* Navbar - SuperSet, Logged in as, Max icon */}
      <Navbar
        userId={userId}
        onViewHistory={() => setShowHistory(true)}
        onSwitchUser={() => {
          clearState()
          setUserInput('')
          setUserGoal('Build strength and improve fitness')
          setMaxWorkoutsPerWeek(4)
          setShowHistory(false)
          setShowQuestInput(false)
          setUserId(null)
        }}
        connectionStatus={connectionStatus}
      />

      <div className="container mx-auto px-4 py-6 max-w-4xl">
        {/* Status Banner - Max-centric, no View past workouts */}
        <StatusBanner
          workoutsCompleted={state?.workouts_completed_this_week || 0}
          maxWorkouts={state?.max_workouts_per_week ?? maxWorkoutsPerWeek}
          fatigueScores={state?.fatigue_scores || {}}
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
            if (window.confirm(`Reset all fatigue scores to zero for ${userId}?`)) {
              sendMessage({ type: 'RESET_FATIGUE' })
            }
          }}
          onResetWorkouts={() => {
            if (window.confirm(`Reset workouts completed counter to zero for ${userId}?`)) {
              sendMessage({ type: 'RESET_WORKOUTS' })
            }
          }}
        />

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-4 bg-red-900/30 border border-red-500/50 rounded-lg">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-red-400 mb-1">Error</h3>
                <p className="text-sm text-red-300">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-red-400 hover:text-red-300"
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

        {/* Greeting from Max - stays visible; buttons appear below after delay */}
        {greetingMessage && (
          <GreetingBanner
            message={greetingMessage}
            onComplete={() => setGreetingComplete(true)}
          />
        )}

        {/* Dashboard: Trust Max & Choose my own path - shown after greeting */}
        {showActionButtons && (
        <div className="mb-6 p-4 bg-[#21262d] rounded-lg border border-[#00CFD1]/20">
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleTrustMax}
              disabled={connectionStatus !== 'connected'}
              className="flex-1 px-6 py-3 bg-[#00CFD1] text-[#0D1117] font-semibold rounded-lg hover:bg-[#00e5e7] disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
            >
              (S) Trust Max
            </button>
            <button
              onClick={() => setShowQuestInput(!showQuestInput)}
              disabled={connectionStatus !== 'connected'}
              className="flex-1 px-6 py-3 bg-transparent border-2 border-[#00CFD1] text-[#00CFD1] font-semibold rounded-lg hover:bg-[#00CFD1]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Choose my own path
            </button>
          </div>
          {showQuestInput && (
            <div className="mt-4 pt-4 border-t border-gray-600 space-y-2">
              <div className="flex gap-2 items-start">
                <MaxMascot size="sm" className="shrink-0 mt-1" />
                <p className="text-sm text-gray-400">Be as specific as you like. I'll use your input to ground the session in the right creator philosophy.</p>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendInput()}
                  placeholder="Tell me about your specific quest... (e.g., 'Focus on core stability for hiking' or 'High-intensity interval training for weight loss')"
                  className="flex-1 px-4 py-3 bg-[#161B22] border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#00CFD1]"
                  autoFocus
                />
                <button
                  onClick={() => handleSendInput()}
                  disabled={connectionStatus !== 'connected' || !userInput.trim()}
                  className="px-6 py-3 bg-[#00CFD1] text-[#0D1117] font-semibold rounded-lg hover:bg-[#00e5e7] disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                >
                  Start My Quest
                </button>
              </div>
            </div>
          )}
          <div className="mt-4 pt-4 border-t border-gray-600">
            <button
              onClick={() => {
                if (window.confirm('Log a rest day? This will reduce your fatigue scores by 30% to simulate recovery.')) {
                  sendMessage({ type: 'LOG_REST' })
                }
              }}
              className="px-4 py-2 text-sm text-gray-400 hover:text-[#00CFD1] hover:bg-[#00CFD1]/10 rounded-lg transition-colors"
              disabled={connectionStatus !== 'connected'}
            >
              🛌 Log Rest Day
            </button>
          </div>
        </div>
        )}

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
        {!workout && connectionStatus === 'connected' && showActionButtons && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-lg">No active workout</p>
            <p className="text-sm mt-2">Trust Max or choose your own path above to start</p>
          </div>
        )}

        {/* Past workouts modal - hidden from main flow, accessible via navbar/settings if needed later */}
        {showHistory && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setShowHistory(false)}>
            <div className="bg-[#21262d] rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col border border-[#00CFD1]/20" onClick={(e) => e.stopPropagation()}>
              <div className="p-4 border-b border-gray-600 flex justify-between items-center">
                <h2 className="text-lg font-semibold text-[#00CFD1]">Past workouts</h2>
                <button type="button" onClick={() => setShowHistory(false)} className="text-gray-400 hover:text-white text-xl leading-none">×</button>
              </div>
              <div className="p-4 overflow-y-auto flex-1">
                {workoutHistory.length === 0 ? (
                  <p className="text-gray-400 text-sm">No past workouts yet.</p>
                ) : (
                  <ul className="space-y-3">
                    {workoutHistory.map((w, i) => {
                      const title = (w as Record<string, string>).focus_area || (w as Record<string, string>).focus_system || (w as Record<string, string>).focus_attribute || 'Workout'
                      const exercises = (w as Record<string, unknown>).exercises as Array<Record<string, unknown>> | undefined
                      const poses = (w as Record<string, unknown>).poses as Array<Record<string, unknown>> | undefined
                      return (
                        <li key={i} className="border border-gray-600 rounded-lg p-3 text-left">
                          <div className="font-medium text-[#00CFD1]">{title}</div>
                          {Array.isArray(exercises) && exercises.length > 0 && (
                            <ul className="mt-2 text-sm text-gray-300 space-y-1">
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
                                    {detail && <span className="text-gray-400">{detail}</span>}
                                  </li>
                                )
                              })}
                            </ul>
                          )}
                          {Array.isArray(poses) && poses.length > 0 && (
                            <ul className="mt-2 text-sm text-gray-300 space-y-1">
                              {poses.map((po, j) => {
                                const name = (po.pose_name as string) || `Pose ${j + 1}`
                                const detail = po.duration != null ? String(po.duration) : ''
                                return (
                                  <li key={j} className="flex justify-between gap-2">
                                    <span>{name}</span>
                                    {detail && <span className="text-gray-400">{detail}</span>}
                                  </li>
                                )
                              })}
                            </ul>
                          )}
                          {(!exercises?.length && !poses?.length) && (
                            <p className="mt-1 text-sm text-gray-400">No exercises listed</p>
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
