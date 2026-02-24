# Feature: Log Rest Day with Fatigue Reduction

## Overview

Added the ability to log rest days from the UI. When a rest day is logged, fatigue scores are reduced by 30% to simulate recovery benefits (sleep, nutrition, active rest, etc.).

## Implementation

### Frontend Changes

1. **App Component** (`frontend/src/App.tsx`):
   - Added "🛌 Log Rest Day" button below the input field
   - Shows confirmation dialog before logging rest
   - Button disabled when WebSocket is not connected
   - Styled as green button to indicate positive action (recovery)

2. **WebSocket Hook** (`frontend/src/hooks/useWorkoutSocket.ts`):
   - Added `LOG_REST` to `ClientMessage` type

### Backend Changes

1. **New Agent Node** (`agents/log_rest.py`):
   - Created `log_rest_node()` function
   - Applies 30% fatigue reduction (multiplies by 0.7)
   - Updates `last_session_timestamp` to current time
   - Ensures fatigue doesn't go below 0

2. **WebSocket Handler** (`backend/main.py`):
   - Added handler for `LOG_REST` message type
   - Calls `log_rest_day()` method
   - Returns updated state with `rest_logged: true` flag

3. **Workout Service** (`backend/services/workout_service.py`):
   - Added `log_rest_day()` method
   - Calls `log_rest_node()` to apply fatigue reduction
   - Updates state via LangGraph checkpoint system

## Fatigue Reduction Logic

### Rest Day Reduction
- **Reduction Factor**: 0.7 (30% reduction)
- **Formula**: `fatigue_new = fatigue_old * 0.7`
- **Applied to**: All muscle groups with non-zero fatigue

### Examples

**Before Rest Day**:
- legs: 0.8
- push: 0.6
- pull: 0.4

**After Rest Day**:
- legs: 0.56 (0.8 * 0.7)
- push: 0.42 (0.6 * 0.7)
- pull: 0.28 (0.4 * 0.7)

### Comparison with Time-Based Decay

**Time-Based Decay** (from `decay.py`):
- Decay factor: 0.97 per hour
- After 24 hours: ~48% reduction
- After 48 hours: ~77% reduction

**Rest Day Logging**:
- Immediate 30% reduction
- More aggressive than 24-hour decay
- Simulates benefits of intentional rest

## User Experience

### How It Works

1. User clicks "🛌 Log Rest Day" button
2. Confirmation dialog: "Log a rest day? This will reduce your fatigue scores by 30%..."
3. If confirmed, fatigue scores are reduced immediately
4. UI updates to show new fatigue scores
5. User can now generate workouts with lower fatigue constraints

### Visual Design

- Green button color (indicates positive/recovery action)
- Rest emoji (🛌) for visual clarity
- Positioned below input field for easy access
- Disabled when not connected

## Use Cases

1. **After Hard Training Block**: User completes 3 hard workouts, logs rest day to recover
2. **Scheduled Rest**: User plans rest day and logs it to reduce fatigue
3. **Recovery from High Fatigue**: Fatigue is 0.9, user logs rest to bring it down to 0.63
4. **Weekly Recovery**: User logs rest day as part of weekly recovery routine

## Technical Details

### State Updates

When rest is logged:
- ✅ Fatigue scores reduced by 30%
- ✅ `last_session_timestamp` updated to current time
- ✅ State persisted via LangGraph checkpoints
- ✅ All other state preserved (workout history, settings, etc.)

### Integration with Decay System

- Rest logging updates `last_session_timestamp`
- Next time decay runs, it calculates from the rest day timestamp
- This prevents "double counting" - rest day provides immediate reduction, then decay continues from that point

## Testing

### Test Case 1: Log Rest with High Fatigue
1. Complete workout (fatigue: 0.8)
2. Click "Log Rest Day"
3. Confirm
4. ✅ Fatigue should reduce to 0.56 (0.8 * 0.7)

### Test Case 2: Log Rest with Multiple Muscle Groups
1. Have fatigue in multiple groups (legs: 0.8, push: 0.6)
2. Log rest day
3. ✅ Both should reduce (legs: 0.56, push: 0.42)

### Test Case 3: Log Rest Then Generate Workout
1. Log rest day (fatigue reduces)
2. Generate new workout
3. ✅ Should generate workout without fatigue constraints
4. ✅ Fatigue scores should remain reduced

### Test Case 4: Log Rest with Zero Fatigue
1. Reset fatigue scores (all 0.0)
2. Log rest day
3. ✅ Fatigue should remain 0.0 (no negative values)

## Files Changed

- `agents/log_rest.py` - New file with rest logging logic
- `frontend/src/App.tsx` - Added Log Rest Day button
- `frontend/src/hooks/useWorkoutSocket.ts` - Added LOG_REST message type
- `backend/main.py` - Added LOG_REST handler
- `backend/services/workout_service.py` - Added log_rest_day() method

## Future Enhancements

Potential improvements:
- [ ] Different rest types (active rest, complete rest, light activity)
- [ ] Rest day duration (half day, full day, multiple days)
- [ ] Muscle-group-specific rest (rest legs but train upper body)
- [ ] Rest day history tracking
- [ ] Automatic rest suggestions based on fatigue
- [ ] Rest day quality metrics (sleep quality, nutrition, etc.)
