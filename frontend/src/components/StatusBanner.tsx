import { useEffect, useState } from 'react'

interface StatusBannerProps {
  workoutsCompleted: number
  maxWorkouts: number
  persona: string
  fatigueScores: Record<string, number>
  userId?: string | null
  onUpdateMaxWorkouts?: (newMax: number) => void | Promise<void>
  onViewHistory?: () => void
  onStartFresh?: () => void
  onResetFatigue?: () => void
  onResetWorkouts?: () => void
}

export default function StatusBanner({
  workoutsCompleted,
  maxWorkouts,
  persona,
  fatigueScores,
  userId,
  onUpdateMaxWorkouts,
  onViewHistory,
  onStartFresh,
  onResetFatigue,
  onResetWorkouts,
}: StatusBannerProps) {
  const [editingMax, setEditingMax] = useState(false)
  const [editValue, setEditValue] = useState(maxWorkouts)
  useEffect(() => {
    setEditValue(maxWorkouts)
  }, [maxWorkouts])

  const progress = maxWorkouts > 0 ? (workoutsCompleted / maxWorkouts) * 100 : 0
  const personaNames: Record<string, string> = {
    iron: 'Coach Iron',
    yoga: 'Zen Flow',
    hiit: 'Inferno HIIT',
    kickboxing: 'Strikeforce',
  }

  // Get top fatigue scores (non-zero)
  const topFatigue = Object.entries(fatigueScores)
    .filter(([_, score]) => score > 0)
    .sort(([_, a], [__, b]) => b - a)
    .slice(0, 3)

  return (
    <div className="mb-6 p-4 bg-white rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            {personaNames[persona] || 'Coach'}
          </h2>
          <p className="text-sm text-gray-600">Active Coach Persona</p>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <div className="flex items-center gap-1">
              {editingMax && onUpdateMaxWorkouts ? (
                <>
                  <input
                    type="number"
                    min={1}
                    max={7}
                    value={editValue}
                    onChange={(e) => setEditValue(Math.min(7, Math.max(1, parseInt(e.target.value, 10) || 1)))}
                    className="w-12 px-1 py-0.5 text-lg font-bold border border-blue-500 rounded"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      onUpdateMaxWorkouts(editValue)
                      setEditingMax(false)
                    }}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEditValue(maxWorkouts)
                      setEditingMax(false)
                    }}
                    className="text-xs text-gray-500 hover:underline"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  {onUpdateMaxWorkouts && (
                    <button
                      type="button"
                      onClick={() => onUpdateMaxWorkouts(Math.max(1, maxWorkouts - 1))}
                      disabled={maxWorkouts <= 1}
                      className="w-7 h-7 rounded border border-gray-300 bg-gray-50 text-gray-700 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-sm font-medium"
                      title="Decrease max workouts per week"
                      aria-label="Decrease max workouts"
                    >
                      −
                    </button>
                  )}
                  <div className="text-2xl font-bold text-blue-600 min-w-[3rem] text-center">
                    {workoutsCompleted}/{maxWorkouts}
                  </div>
                  {onUpdateMaxWorkouts && (
                    <>
                      <button
                        type="button"
                        onClick={() => onUpdateMaxWorkouts(Math.min(7, maxWorkouts + 1))}
                        disabled={maxWorkouts >= 7}
                        className="w-7 h-7 rounded border border-gray-300 bg-gray-50 text-gray-700 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-sm font-medium"
                        title="Increase max workouts per week"
                        aria-label="Increase max workouts"
                      >
                        +
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingMax(true)}
                        className="text-xs text-gray-500 hover:text-blue-600 ml-0.5"
                        title="Edit max workouts per week"
                      >
                        ✎
                      </button>
                    </>
                  )}
                </>
              )}
            </div>
            <p className="text-xs text-gray-500 w-full text-right">Workouts this week</p>
            {onResetWorkouts && workoutsCompleted > 0 && (
              <button
                onClick={onResetWorkouts}
                className="text-xs text-red-600 hover:text-red-700 hover:underline"
                title="Reset workouts completed counter to zero"
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </div>

      {/* View history / Start fresh */}
      <div className="flex flex-wrap gap-2 mb-3">
        {onViewHistory && (
          <button
            type="button"
            onClick={onViewHistory}
            className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
          >
            View past workouts
          </button>
        )}
        {onStartFresh && (
          <button
            type="button"
            onClick={onStartFresh}
            className="text-sm text-gray-500 hover:text-red-600 hover:underline"
            title="Delete all history and start over"
          >
            Start fresh
          </button>
        )}
      </div>

      {/* Progress Ring */}
      <div className="mb-3">
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      </div>

      {/* Fatigue Scores */}
      {topFatigue.length > 0 && (
        <div className="flex items-center justify-between">
          <div className="flex gap-4 text-sm">
            <span className="text-gray-600 font-medium">Fatigue:</span>
            {topFatigue.map(([muscle, score]) => (
              <span key={muscle} className="text-gray-700">
                {muscle}: <span className="font-semibold">{score.toFixed(2)}</span>
              </span>
            ))}
          </div>
          {onResetFatigue && (
            <button
              onClick={onResetFatigue}
              className="text-xs text-red-600 hover:text-red-700 hover:underline"
              title="Reset all fatigue scores to zero for your account"
            >
              Reset Fatigue
            </button>
          )}
        </div>
      )}
    </div>
  )
}
