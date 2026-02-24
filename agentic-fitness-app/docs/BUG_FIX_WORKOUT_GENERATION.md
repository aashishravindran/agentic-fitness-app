# Bug Fix - Workout Not Generating After Finishing One

## Problem

After finishing a workout, users couldn't generate a new workout. The workflow was:
1. User logs in
2. User asks for workout → ✅ Works
3. User finishes workout → ✅ Works
4. User asks for another workout → ❌ Doesn't work

## Root Cause

After `finalize_workout_node` completed, it:
- Saved workout to history ✅
- Incremented workout counter ✅
- Applied fatigue ✅
- Set `is_working_out = False` ✅
- **BUT didn't clear `daily_workout`** ❌

This meant:
1. The old workout remained in state
2. When starting a new workout, `run_workout` would load existing state and preserve the old `daily_workout`
3. The graph might see the existing workout and not generate a new one, or the frontend might show the old workout

## Solution

### Fix 1: Clear `daily_workout` in `finalize_workout_node`

Modified `agents/finalize_workout.py` to explicitly clear `daily_workout` and `current_workout` after finalizing:

```python
return {
    "workout_history": history,
    "workouts_completed_this_week": workouts_completed,
    "fatigue_scores": fatigue_scores,
    "active_logs": [],
    "is_working_out": False,
    "daily_workout": None,  # Clear daily_workout after finalizing
    "current_workout": None,  # Clear current_workout as well
}
```

### Fix 2: Clear `daily_workout` when starting new workout

Modified `graph.py` in `run_workout()` to always clear `daily_workout` when starting a new workout request:

```python
# IMPORTANT: Clear daily_workout when starting a new workout request
# This ensures we don't keep the old workout when generating a new one
initial_state["daily_workout"] = None
initial_state["current_workout"] = None
initial_state["is_working_out"] = False
```

### Fix 3: Ensure frontend clears workout on completion

Updated `frontend/src/hooks/useWorkoutSocket.ts` to properly handle `workout: null`:

```typescript
// Always update workout - if it's None/null, clear it
if (message.workout !== undefined) {
  setWorkout(message.workout || null)
}
```

## Files Changed

1. `agents/finalize_workout.py` - Clear `daily_workout` after finalizing
2. `graph.py` - Clear `daily_workout` when starting new workout
3. `frontend/src/hooks/useWorkoutSocket.ts` - Properly handle null workout

## Testing

### Test Case:
1. Log in as user1
2. Ask for workout → ✅ Should generate workout
3. Finish workout → ✅ Should save to history
4. Ask for another workout → ✅ Should generate new workout (not show old one)
5. Repeat steps 2-4 multiple times → ✅ Should work each time

## Technical Details

### State Flow

**Before Fix:**
```
Workout 1 → Finish → daily_workout still set → Try Workout 2 → Old workout persists
```

**After Fix:**
```
Workout 1 → Finish → daily_workout cleared → Try Workout 2 → New workout generated
```

### Why This Matters

- `daily_workout` is the active workout plan displayed in the UI
- If it's not cleared, the UI shows the old workout
- The graph might also check for existing workouts and skip generation
- Clearing it ensures a clean slate for each new workout request
