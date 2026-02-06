interface StatusBannerProps {
  workoutsCompleted: number
  maxWorkouts: number
  persona: string
  fatigueScores: Record<string, number>
  onResetFatigue?: () => void
  onResetWorkouts?: () => void
}

export default function StatusBanner({
  workoutsCompleted,
  maxWorkouts,
  persona,
  fatigueScores,
  onResetFatigue,
  onResetWorkouts,
}: StatusBannerProps) {
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
          <div className="flex items-center gap-2">
            <div>
              <div className="text-2xl font-bold text-blue-600">
                {workoutsCompleted}/{maxWorkouts}
              </div>
              <p className="text-xs text-gray-500">Workouts this week</p>
            </div>
            {onResetWorkouts && workoutsCompleted > 0 && (
              <button
                onClick={onResetWorkouts}
                className="text-xs text-red-600 hover:text-red-700 hover:underline ml-2"
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
