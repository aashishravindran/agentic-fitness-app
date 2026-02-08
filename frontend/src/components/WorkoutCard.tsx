import { useState } from 'react'
import RPESelector from './RPESelector'

interface WorkoutCardProps {
  workout: any
  isWorkingOut: boolean
  onLogSet: (exerciseName: string, exerciseId: string | null, weight: number, reps: number, rpe: number) => void
  onFinishWorkout: () => void
}

export default function WorkoutCard({
  workout,
  isWorkingOut,
  onLogSet,
  onFinishWorkout,
}: WorkoutCardProps) {
  const [selectedExercise, setSelectedExercise] = useState<string | null>(null)
  const [selectedExerciseId, setSelectedExerciseId] = useState<string | null>(null)
  const [weight, setWeight] = useState<string>('')
  const [reps, setReps] = useState<string>('')
  const [rpe, setRpe] = useState<number>(5)

  const handleLogSet = () => {
    if (!selectedExercise) return
    
    const weightNum = parseFloat(weight) || 0
    const repsNum = parseInt(reps) || 0
    
    if (repsNum > 0 && rpe >= 1 && rpe <= 10) {
      onLogSet(selectedExercise, selectedExerciseId, weightNum, repsNum, rpe)
      setWeight('')
      setReps('')
      setRpe(5)
    }
  }

  const exercises = workout?.exercises || []
  const poses = workout?.poses || []
  const focus = workout?.focus_area || workout?.focus_system || workout?.focus_attribute || 'General'

  return (
    <div className="mb-6 p-6 bg-white rounded-lg shadow-md">
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Today's Workout</h2>
        <p className="text-sm text-gray-600">Focus: <span className="font-semibold">{focus}</span></p>
        {workout?.overall_rationale && (
          <p className="text-sm text-gray-600 mt-2">{workout.overall_rationale}</p>
        )}
      </div>

      {/* Exercises */}
      {exercises.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-700 mb-3">Exercises</h3>
          <div className="space-y-4">
            {exercises.map((exercise: any, index: number) => (
              <div
                key={index}
                className={`p-4 border-2 rounded-lg ${
                  selectedExercise === exercise.exercise_name
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-semibold text-gray-800">{exercise.exercise_name}</h4>
                    <p className="text-sm text-gray-600">
                      Sets: {exercise.sets} | Reps: {exercise.reps}
                    </p>
                    {exercise.tempo_notes && (
                      <p className="text-xs text-gray-500 mt-1">Tempo: {exercise.tempo_notes}</p>
                    )}
                  </div>
                  {isWorkingOut && (
                    <button
                      onClick={() => {
                        setSelectedExercise(exercise.exercise_name)
                        setSelectedExerciseId(exercise.id ?? null)
                      }}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Log Set
                    </button>
                  )}
                </div>

                {/* Log Set Form */}
                {selectedExercise === exercise.exercise_name && isWorkingOut && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Weight (kg)
                        </label>
                        <input
                          type="number"
                          value={weight}
                          onChange={(e) => setWeight(e.target.value)}
                          placeholder="0"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Reps
                        </label>
                        <input
                          type="number"
                          value={reps}
                          onChange={(e) => setReps(e.target.value)}
                          placeholder="0"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>

                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        RPE (Rate of Perceived Exertion)
                      </label>
                      <RPESelector value={rpe} onChange={setRpe} />
                    </div>

                    <button
                      onClick={handleLogSet}
                      className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                    >
                      Log Set
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Yoga Poses */}
      {poses.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-700 mb-3">Poses</h3>
          <div className="space-y-3">
            {poses.map((pose: any, index: number) => (
              <div key={index} className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-semibold text-gray-800">{pose.pose_name}</h4>
                {pose.duration && (
                  <p className="text-sm text-gray-600">Duration: {pose.duration}</p>
                )}
                {pose.focus_area && (
                  <p className="text-xs text-gray-500 mt-1">Focus: {pose.focus_area}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Finish Workout Button */}
      {isWorkingOut && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <button
            onClick={onFinishWorkout}
            className="w-full px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors"
          >
            Finish Workout
          </button>
        </div>
      )}
    </div>
  )
}
