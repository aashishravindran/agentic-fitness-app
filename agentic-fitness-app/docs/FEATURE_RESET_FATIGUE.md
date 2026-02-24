# Feature: Reset Fatigue Scores

## Overview

Added the ability to reset fatigue scores from the UI without deleting all user data. This allows users to manually clear their fatigue levels when needed (e.g., after a rest period, testing, or if fatigue scores seem incorrect).

## Implementation

### Frontend Changes

1. **StatusBanner Component** (`frontend/src/components/StatusBanner.tsx`):
   - Added `onResetFatigue` callback prop
   - Added "Reset Fatigue" button next to fatigue scores display
   - Button only shows when there are fatigue scores to display
   - Styled as a small red text link for subtle but accessible UI

2. **App Component** (`frontend/src/App.tsx`):
   - Added `onResetFatigue` handler that:
     - Shows confirmation dialog before resetting
     - Sends `RESET_FATIGUE` message via WebSocket

3. **WebSocket Hook** (`frontend/src/hooks/useWorkoutSocket.ts`):
   - Added `RESET_FATIGUE` to `ClientMessage` type

### Backend Changes

1. **WebSocket Handler** (`backend/main.py`):
   - Added handler for `RESET_FATIGUE` message type
   - Calls `reset_fatigue_scores()` method
   - Returns updated state to frontend

2. **Workout Service** (`backend/services/workout_service.py`):
   - Added `reset_fatigue_scores()` method
   - Resets all fatigue scores to 0.0 (defaults)
   - Preserves all other state (workout history, settings, etc.)
   - Updates state via LangGraph checkpoint system

## User Experience

### How It Works

1. User sees fatigue scores displayed in StatusBanner
2. User clicks "Reset Fatigue" button
3. Confirmation dialog appears: "Reset all fatigue scores to zero?"
4. If confirmed, fatigue scores are reset to 0.0
5. UI updates immediately with cleared fatigue scores
6. User can now generate workouts without fatigue constraints

### Visual Design

- Button appears inline with fatigue scores
- Small, red text link style
- Hover effect for better UX
- Only visible when fatigue scores exist
- Positioned on the right side for easy access

## Technical Details

### Fatigue Score Reset

When reset, all fatigue scores are set to:
```python
{
    "legs": 0.0, "push": 0.0, "pull": 0.0,
    "spine": 0.0, "hips": 0.0, "shoulders": 0.0,
    "cardio": 0.0, "cns": 0.0,
    "coordination": 0.0, "speed": 0.0, "endurance": 0.0,
}
```

### State Preservation

The reset **preserves**:
- ✅ Workout history
- ✅ Workouts completed this week
- ✅ Max workouts per week setting
- ✅ Fatigue threshold setting
- ✅ Current workout (if any)
- ✅ Active logs (if any)
- ✅ All other state fields

The reset **only clears**:
- ❌ Fatigue scores (all set to 0.0)

## Use Cases

1. **After Rest Period**: User took a week off and wants to reset fatigue
2. **Testing**: Developer/user wants to test workout generation without fatigue constraints
3. **Correction**: Fatigue scores seem incorrect and user wants to start fresh
4. **New Training Cycle**: Starting a new training block and resetting fatigue

## Testing

### Test Case 1: Reset Fatigue with Active Scores
1. Generate and finish a workout (builds fatigue)
2. Check fatigue scores in StatusBanner
3. Click "Reset Fatigue"
4. Confirm in dialog
5. ✅ Fatigue scores should all be 0.0
6. ✅ Workout history should still be present

### Test Case 2: Reset Fatigue Without Confirmation
1. Click "Reset Fatigue"
2. Cancel in dialog
3. ✅ Fatigue scores should remain unchanged

### Test Case 3: Generate Workout After Reset
1. Reset fatigue scores
2. Generate a new workout
3. ✅ Should generate workout without fatigue constraints
4. ✅ Should not suggest recovery due to fatigue

## Future Enhancements

Potential improvements:
- [ ] Reset individual muscle groups instead of all
- [ ] Set custom fatigue values (not just zero)
- [ ] Undo/redo fatigue reset
- [ ] Fatigue reset history/audit log
- [ ] Bulk reset options (fatigue + workouts completed, etc.)
