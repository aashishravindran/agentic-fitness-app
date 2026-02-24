# Bug Fixes - Persona & User Switching

## Issues Fixed

### 1. ✅ Persona Not Being Used When Changed

**Problem**: When changing the persona dropdown (Iron/Yoga/HIIT/Kickboxing) and sending a message, the workout was still generated using the previous persona from the saved state.

**Root Cause**: The `run_workout()` function in `graph.py` was loading existing state and merging it, but it wasn't overriding the `selected_persona` field with the new persona parameter.

**Solution**: 
- Modified `graph.py` to always override `selected_persona` and `selected_creator` with the new persona parameter, even when loading existing state
- This ensures that when a user changes the persona dropdown, the new persona is always used

**Files Changed**:
- `graph.py` - Added explicit persona override after loading existing state

### 2. ✅ Switch User Showing Old User's Workout

**Problem**: When clicking "Switch User", the old user's workout and state were still displayed until a new workout was generated.

**Root Cause**: The Zustand store wasn't being cleared when the userId changed, so the old user's state/workout persisted in the UI.

**Solution**:
- Added `clearState()` function to the Zustand store
- Call `clearState()` when:
  - User logs in (new user)
  - User clicks "Switch User"
  - userId changes in the WebSocket hook

**Files Changed**:
- `frontend/src/store/workoutStore.ts` - Added `clearState()` function
- `frontend/src/App.tsx` - Call `clearState()` on login and switch user
- `frontend/src/hooks/useWorkoutSocket.ts` - Call `clearState()` when userId changes

## Testing

### Test Persona Change:
1. Log in as a user
2. Select "Iron" persona and send "I want a workout"
3. Note the workout type
4. Change persona dropdown to "Yoga"
5. Send "I want a yoga workout"
6. ✅ Should generate a yoga-style workout (poses, not exercises)

### Test User Switch:
1. Log in as "user1"
2. Generate a workout
3. Click "Switch User"
4. ✅ Old workout should disappear immediately
5. Log in as "user2"
6. ✅ Should see empty state (no workout from user1)

## Technical Details

### Persona Override Logic

In `graph.py`, after loading existing state:
```python
# IMPORTANT: Always override selected_persona with the new persona parameter
# This ensures persona changes are respected
initial_state["selected_persona"] = persona
initial_state["selected_creator"] = persona  # Legacy compatibility
```

### State Clearing

The `clearState()` function resets all store values:
```typescript
clearState: () => set({ 
  state: null, 
  workout: null, 
  isWorkingOut: false, 
  error: null 
})
```

This is called whenever the userId changes to ensure a clean slate for the new user.
