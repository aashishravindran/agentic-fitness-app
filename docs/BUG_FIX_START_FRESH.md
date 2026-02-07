# Bug Fix - "Start Fresh" Not Working

## Problem

The "New user (start fresh)" checkbox in the login screen was not functional. When checked, it didn't actually reset/delete the user's existing state, so users with existing data would still see their old workouts and history.

## Root Cause

The `isNewUser` state was tracked in the `LoginScreen` component but:
1. It was never passed to the `onLogin` callback
2. The backend had no logic to handle resetting user state
3. There was no way to delete user checkpoints when "start fresh" was selected

## Solution

### Frontend Changes

1. **Updated `LoginScreen.tsx`**:
   - Modified `onLogin` callback to accept `startFresh` parameter
   - Pass `isNewUser` flag when calling `onLogin`

2. **Updated `App.tsx`**:
   - Accept `startFresh` parameter in `handleLogin`
   - Store reset flag in state
   - Use `useEffect` to send `RESET_USER` message when WebSocket connects

3. **Updated `useWorkoutSocket.ts`**:
   - Added `RESET_USER` to `ClientMessage` type
   - Added `user_reset` flag to `ServerMessage` type
   - Handle `user_reset` response to clear state

### Backend Changes

1. **Updated `workout_service.py`**:
   - Added `reset_user_state()` method that calls `delete_user()` from `db_utils`
   - Deletes all checkpoints for the user

2. **Updated `main.py`**:
   - Added handler for `RESET_USER` message type
   - Calls `reset_user_state()` and sends confirmation

## How It Works

1. User checks "New user (start fresh)" checkbox
2. User logs in → `isNewUser` flag is passed to `handleLogin`
3. `shouldReset` state is set to `true`
4. When WebSocket connects, `useEffect` detects connection + reset flag
5. Sends `RESET_USER` message to backend
6. Backend deletes all checkpoints for that user
7. Backend sends confirmation with `user_reset: true`
8. Frontend clears all state (state, workout, isWorkingOut)

## Files Changed

- `frontend/src/components/LoginScreen.tsx` - Pass `startFresh` flag
- `frontend/src/App.tsx` - Handle reset flag and send message
- `frontend/src/hooks/useWorkoutSocket.ts` - Handle RESET_USER message
- `backend/services/workout_service.py` - Add `reset_user_state()` method
- `backend/main.py` - Handle RESET_USER message type

## Testing

### Test Case 1: Start Fresh for New User
1. Log in with a new user ID
2. Check "New user (start fresh)"
3. Generate a workout
4. Finish workout
5. Log out and log back in with same ID (unchecked)
6. ✅ Should see previous workout history

### Test Case 2: Start Fresh for Existing User
1. Log in with existing user ID (unchecked)
2. Generate and finish a workout
3. Log out
4. Log back in with same ID, check "New user (start fresh)"
5. ✅ Should NOT see previous workout history
6. ✅ Should start with fresh state (no workouts completed, default fatigue)

### Test Case 3: Start Fresh Then Generate Workout
1. Log in with existing user, check "start fresh"
2. Wait for connection
3. Generate a workout
4. ✅ Should work normally with fresh state

## Technical Details

### Database Deletion

The `reset_user_state()` method uses `delete_user()` from `db_utils`, which:
- Deletes all rows from `checkpoints` table where `thread_id = user_id`
- Effectively removes all state history for that user
- Returns `True` if deletion was successful

### State Clearing

When `user_reset: true` is received:
- Frontend clears `state`, `workout`, and `isWorkingOut` from Zustand store
- User starts with completely fresh state
- Next workout generation will use default fatigue scores
