# Bug Fix: Switch User Not Clearing State

## Problem

When clicking "Switch User", the old user's state (workout, fatigue scores, etc.) was still visible when logging in as a new user. The state wasn't being properly cleared.

## Root Cause

1. **State clearing timing**: State was cleared but WebSocket might reconnect and send old state before clearing completed
2. **Initial state on connect**: When a new user connected, the backend sent initial state if available, which could show old data
3. **Race condition**: State clearing and WebSocket reconnection happened simultaneously, causing race conditions

## Solution

### Frontend Changes

1. **App.tsx - Enhanced Switch User**:
   - Clear all local state immediately (userInput, persona, shouldReset)
   - Set userId to null last to trigger proper cleanup sequence
   - Ensures all state is cleared before showing login screen

2. **useWorkoutSocket.ts - Improved State Clearing**:
   - Clear state immediately when userId changes (including null)
   - Add small delay before connecting to ensure state is cleared first
   - Proper cleanup of timeouts and connections

3. **useWorkoutSocket.ts - Handle Null State**:
   - Explicitly handle `state: null` in AGENT_RESPONSE messages
   - Clear state when backend sends null (indicates new user with no data)

### Backend Changes

1. **main.py - Better Initial State Handling**:
   - Only send initial state if it has meaningful data (workout or history)
   - Send explicit `state: null` for new users to ensure frontend clears state
   - Prevents showing stale data for new users

2. **graph.py - Rest Day Logging**:
   - Added `log_rest_day()` function that uses the graph system
   - Properly integrates with checkpoint system
   - Ensures rest day logging goes through the graph workflow

3. **workout_service.py - Use Graph for Rest Day**:
   - Updated `log_rest_day()` to use `graph.log_rest_day()`
   - Ensures consistency with graph-based operations

## How It Works Now

### Switch User Flow

1. User clicks "Switch User"
2. **Immediate actions**:
   - `clearState()` called → Zustand store cleared
   - `setUserInput('')` → Input cleared
   - `setPersona('iron')` → Persona reset
   - `setShouldReset(false)` → Reset flag cleared
   - `setUserId(null)` → Triggers WebSocket disconnect
3. **WebSocket cleanup**:
   - Connection closed
   - State cleared again in useEffect
   - Connection status set to 'disconnected'
4. **Login screen shown**:
   - Clean state, no old data visible
5. **New user logs in**:
   - WebSocket connects with new userId
   - Backend sends `state: null` if no data exists
   - Frontend receives null and clears any remaining state
   - Fresh start for new user

### Rest Day Logging Through Graph

1. User clicks "Log Rest Day"
2. Frontend sends `LOG_REST` message
3. Backend calls `workout_service.log_rest_day()`
4. Service calls `graph.log_rest_day()`
5. Graph function:
   - Gets current state from checkpoint
   - Applies `log_rest_node()` to reduce fatigue
   - Updates state via graph checkpoint system
   - Returns updated state
6. Frontend receives updated state with reduced fatigue

## Files Changed

- `frontend/src/App.tsx` - Enhanced switch user button
- `frontend/src/hooks/useWorkoutSocket.ts` - Improved state clearing and null handling
- `backend/main.py` - Better initial state handling
- `graph.py` - Added `log_rest_day()` function
- `backend/services/workout_service.py` - Use graph for rest day logging

## Testing

### Test Case 1: Switch User Clears State
1. Log in as "user1"
2. Generate a workout
3. Click "Switch User"
4. ✅ All state should be cleared immediately
5. ✅ Login screen should show (no workout visible)
6. Log in as "user2"
7. ✅ Should see empty state (no user1's workout)

### Test Case 2: Switch User Then New User
1. Log in as "user1", generate workout
2. Click "Switch User"
3. Log in as "user2" (new user, no data)
4. ✅ Backend should send `state: null`
5. ✅ Frontend should show empty state
6. ✅ No old workout should be visible

### Test Case 3: Rest Day Through Graph
1. Log in as user
2. Complete workout (fatigue: 0.8)
3. Click "Log Rest Day"
4. ✅ Fatigue should reduce to 0.56 (0.8 * 0.7)
5. ✅ State should be persisted via graph checkpoint

## Technical Details

### State Clearing Sequence

**Before Fix**:
```
Switch User → clearState() → setUserId(null) → WebSocket disconnects → 
New user connects → Old state might still be visible
```

**After Fix**:
```
Switch User → clearState() + clear all local state → setUserId(null) → 
WebSocket disconnects + clears state → New user connects → 
Backend sends null if no data → Frontend clears state → Clean start
```

### Rest Day Through Graph

The rest day logging now goes through the graph system:
- Uses `app.get_state()` to get current state
- Applies `log_rest_node()` to reduce fatigue
- Uses `app.update_state()` to persist changes
- Returns updated state via `app.get_state()`

This ensures consistency with other graph operations and proper checkpoint handling.
