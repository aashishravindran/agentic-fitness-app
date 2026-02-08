import { useEffect, useState } from 'react'

interface StatusBannerProps {
  workoutsCompleted: number
  maxWorkouts: number
  fatigueScores: Record<string, number>
  onUpdateMaxWorkouts?: (newMax: number) => void | Promise<void>
  onResetFatigue?: () => void
  onResetWorkouts?: () => void
}

export default function StatusBanner({
  workoutsCompleted,
  maxWorkouts,
  fatigueScores,
  onUpdateMaxWorkouts,
  onResetFatigue,
  onResetWorkouts,
}: StatusBannerProps) {
  const [editingMax, setEditingMax] = useState(false)
  const [editValue, setEditValue] = useState(maxWorkouts)
  useEffect(() => {
    setEditValue(maxWorkouts)
  }, [maxWorkouts])

  const progress = maxWorkouts > 0 ? (workoutsCompleted / maxWorkouts) * 100 : 0

  // Get top fatigue scores (non-zero)
  const topFatigue = Object.entries(fatigueScores)
    .filter(([_, score]) => score > 0)
    .sort(([_, a], [__, b]) => b - a)
    .slice(0, 3)

  return (
    <div className="mb-6 p-4 bg-[#21262d] rounded-lg border border-[#00CFD1]/20">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-lg font-semibold text-[#00CFD1]">Max</h2>
          <p className="text-sm text-gray-400">Your Coach</p>
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
                    className="w-12 px-1 py-0.5 text-lg font-bold border border-[#00CFD1] rounded bg-[#161B22] text-white"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      onUpdateMaxWorkouts(editValue)
                      setEditingMax(false)
                    }}
                    className="text-xs text-[#00CFD1] hover:underline"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEditValue(maxWorkouts)
                      setEditingMax(false)
                    }}
                    className="text-xs text-gray-400 hover:underline"
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
                      className="w-7 h-7 rounded border border-gray-600 bg-[#161B22] text-gray-300 hover:bg-[#21262d] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-sm font-medium"
                      title="Decrease max workouts per week"
                      aria-label="Decrease max workouts"
                    >
                      −
                    </button>
                  )}
                  <div className="text-2xl font-bold text-[#00CFD1] min-w-[3rem] text-center">
                    {workoutsCompleted}/{maxWorkouts}
                  </div>
                  {onUpdateMaxWorkouts && (
                    <>
                      <button
                        type="button"
                        onClick={() => onUpdateMaxWorkouts(Math.min(7, maxWorkouts + 1))}
                        disabled={maxWorkouts >= 7}
                        className="w-7 h-7 rounded border border-gray-600 bg-[#161B22] text-gray-300 hover:bg-[#21262d] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-sm font-medium"
                        title="Increase max workouts per week"
                        aria-label="Increase max workouts"
                      >
                        +
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingMax(true)}
                        className="text-xs text-gray-400 hover:text-[#00CFD1] ml-0.5"
                        title="Edit max workouts per week"
                      >
                        ✎
                      </button>
                    </>
                  )}
                </>
              )}
            </div>
            <p className="text-xs text-gray-400 w-full text-right">Workouts this week</p>
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

      {/* Progress Ring */}
      <div className="mb-3">
        <div className="w-full bg-gray-700 rounded-full h-3">
          <div
            className="bg-[#00CFD1] h-3 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      </div>

      {/* Fatigue Scores */}
      {topFatigue.length > 0 && (
        <div className="flex items-center justify-between">
          <div className="flex gap-4 text-sm">
            <span className="text-gray-400 font-medium">Fatigue:</span>
            {topFatigue.map(([muscle, score]) => (
              <span key={muscle} className="text-gray-300">
                {muscle}: <span className="font-semibold">{score.toFixed(2)}</span>
              </span>
            ))}
          </div>
          {onResetFatigue && (
            <button
              onClick={onResetFatigue}
              className="text-xs text-red-400 hover:text-red-300 hover:underline"
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
