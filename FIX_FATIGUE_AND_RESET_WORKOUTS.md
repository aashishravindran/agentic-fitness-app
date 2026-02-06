# Fix: Fatigue Spikes & Reset Workouts Feature

## Problem 1: Fatigue Spiking Too High After One Workout

### Issue
After completing just one workout, fatigue scores were reaching 0.8+ (the threshold), causing the system to automatically suggest recovery/rest for the next workout.

### Root Cause
The fatigue increments were too aggressive:
- **RPE 8-10**: +0.6 fatigue (too high!)
- **RPE 5-7**: +0.4 fatigue
- **RPE < 5**: +0.2 fatigue
- **Default (no logs)**: +0.5 fatigue

With default starting fatigue of 0.2, a single workout with RPE 9 would push fatigue to 0.8, immediately triggering the recovery threshold.

### Solution
Reduced fatigue increments to more reasonable values:
- **RPE 8-10**: +0.25 fatigue (reduced from 0.6)
- **RPE 5-7**: +0.15 fatigue (reduced from 0.4)
- **RPE < 5**: +0.1 fatigue (reduced from 0.2)
- **Default (no logs)**: +0.2 fatigue (reduced from 0.5)

### Impact
Now a user can complete multiple workouts before fatigue reaches the threshold:
- Starting fatigue: 0.2
- After workout 1 (RPE 9): 0.45
- After workout 2 (RPE 9): 0.70
- After workout 3 (RPE 9): 0.95 (would trigger recovery)

This allows for 2-3 hard workouts before recovery is suggested, which is more realistic.

## Problem 2: Need to Reset Workouts Counter

### Issue
Users wanted a way to reset the `workouts_completed_this_week` counter without deleting all their data.

### Solution
Added a "Reset" button next to the workouts counter in the StatusBanner component.

## Implementation

### Frontend Changes

1. **StatusBanner Component** (`frontend/src/components/StatusBanner.tsx`):
   - Added `onResetWorkouts` callback prop
   - Added "Reset" button next to workouts counter
   - Button only shows when `workoutsCompleted > 0`
   - Styled as small red text link

2. **App Component** (`frontend/src/App.tsx`):
   - Added `onResetWorkouts` handler with confirmation dialog
   - Sends `RESET_WORKOUTS` message via WebSocket

3. **WebSocket Hook** (`frontend/src/hooks/useWorkoutSocket.ts`):
   - Added `RESET_WORKOUTS` to `ClientMessage` type

### Backend Changes

1. **WebSocket Handler** (`backend/main.py`):
   - Added handler for `RESET_WORKOUTS` message type
   - Calls `reset_workouts_completed()` method
   - Returns updated state to frontend

2. **Workout Service** (`backend/services/workout_service.py`):
   - Added `reset_workouts_completed()` method
   - Resets `workouts_completed_this_week` to 0
   - Preserves all other state (workout history, fatigue, settings, etc.)

3. **Fatigue Calculation** (`agents/finalize_workout.py`):
   - Reduced all fatigue increment values
   - More realistic fatigue accumulation over multiple workouts

## User Experience

### Reset Workouts Button
- Appears next to "Workouts this week" counter
- Only visible when workouts completed > 0
- Shows confirmation dialog before resetting
- Resets counter to 0, preserves everything else

### Fatigue Behavior
- Users can now complete 2-3 hard workouts before fatigue threshold
- More realistic progression
- Recovery suggestions appear at appropriate times

## Testing

### Test Case 1: Fatigue After Multiple Workouts
1. Start with default fatigue (0.2)
2. Complete workout 1 with RPE 9 → Fatigue: 0.45 ✅
3. Complete workout 2 with RPE 9 → Fatigue: 0.70 ✅
4. Complete workout 3 with RPE 9 → Fatigue: 0.95 → Recovery suggested ✅

### Test Case 2: Reset Workouts Counter
1. Complete 2 workouts (counter shows 2/4)
2. Click "Reset" next to counter
3. Confirm in dialog
4. ✅ Counter resets to 0/4
5. ✅ Workout history still present
6. ✅ Fatigue scores unchanged

### Test Case 3: Reset Workouts Then Generate Workout
1. Reset workouts counter
2. Generate a new workout
3. ✅ Should generate workout (not blocked by weekly limit)
4. ✅ Counter increments correctly

## Files Changed

- `agents/finalize_workout.py` - Reduced fatigue increments
- `frontend/src/components/StatusBanner.tsx` - Added reset workouts button
- `frontend/src/App.tsx` - Added reset workouts handler
- `frontend/src/hooks/useWorkoutSocket.ts` - Added RESET_WORKOUTS message type
- `backend/main.py` - Added RESET_WORKOUTS handler
- `backend/services/workout_service.py` - Added reset_workouts_completed() method

## Technical Details

### Fatigue Increments (Before → After)

| RPE Range | Before | After | Change |
|-----------|--------|-------|--------|
| 8-10 (High) | +0.6 | +0.25 | -58% |
| 5-7 (Mid) | +0.4 | +0.15 | -63% |
| < 5 (Low) | +0.2 | +0.1 | -50% |
| Default | +0.5 | +0.2 | -60% |

### State Preservation

When resetting workouts counter, **preserves**:
- ✅ Workout history
- ✅ Fatigue scores
- ✅ Max workouts per week setting
- ✅ Fatigue threshold setting
- ✅ Current workout (if any)
- ✅ All other state fields

The reset **only clears**:
- ❌ `workouts_completed_this_week` (set to 0)

## Future Enhancements

Potential improvements:
- [ ] Configurable fatigue increments per user
- [ ] Fatigue decay rate adjustment
- [ ] Visual fatigue history chart
- [ ] Automatic weekly reset option
- [ ] Per-muscle-group fatigue reset
