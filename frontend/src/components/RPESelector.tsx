interface RPESelectorProps {
  value: number
  onChange: (value: number) => void
}

export default function RPESelector({ value, onChange }: RPESelectorProps) {
  const getColor = (rpe: number) => {
    if (rpe <= 3) return 'bg-green-500'
    if (rpe <= 6) return 'bg-yellow-500'
    if (rpe <= 8) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const getLabel = (rpe: number) => {
    if (rpe <= 3) return 'Easy'
    if (rpe <= 6) return 'Moderate'
    if (rpe <= 8) return 'Hard'
    return 'Max Effort'
  }

  return (
    <div className="w-full">
      {/* Slider */}
      <input
        type="range"
        min="1"
        max="10"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        style={{
          background: `linear-gradient(to right, #10b981 0%, #fbbf24 30%, #f97316 60%, #ef4444 100%)`,
        }}
      />

      {/* Labels */}
      <div className="flex justify-between mt-2 text-xs text-gray-600">
        <span>1</span>
        <span>5</span>
        <span>10</span>
      </div>

      {/* Current Value Display */}
      <div className="mt-4 flex items-center justify-center gap-4">
        <div className={`px-4 py-2 rounded-lg ${getColor(value)} text-white font-semibold text-lg`}>
          RPE {value}
        </div>
        <div className="text-sm text-gray-600">
          {getLabel(value)}
        </div>
      </div>

      {/* Warning for high RPE */}
      {value >= 9 && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800 font-medium">
            ⚠️ High RPE detected! This will significantly increase fatigue scores.
          </p>
        </div>
      )}
    </div>
  )
}
