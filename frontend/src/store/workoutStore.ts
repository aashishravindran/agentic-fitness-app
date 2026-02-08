import { create } from 'zustand'

interface WorkoutState {
  state: any | null
  workout: any | null
  isWorkingOut: boolean
  greetingMessage: string | null
  error: string | null
  setState: (state: any) => void
  setWorkout: (workout: any) => void
  setIsWorkingOut: (isWorkingOut: boolean) => void
  setGreetingMessage: (msg: string | null) => void
  setError: (error: string | null) => void
  clearState: () => void
}

export const useWorkoutStore = create<WorkoutState>((set) => ({
  state: null,
  workout: null,
  isWorkingOut: false,
  greetingMessage: null,
  error: null,
  setState: (state) => set({ state }),
  setWorkout: (workout) => set({ workout }),
  setIsWorkingOut: (isWorkingOut) => set({ isWorkingOut }),
  setGreetingMessage: (greetingMessage) => set({ greetingMessage }),
  setError: (error) => set({ error }),
  clearState: () => set({ 
    state: null, 
    workout: null, 
    isWorkingOut: false, 
    greetingMessage: null,
    error: null 
  }),
}))
