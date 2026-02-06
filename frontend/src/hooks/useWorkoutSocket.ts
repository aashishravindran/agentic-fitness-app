import { useEffect, useRef, useState } from 'react'
import { useWorkoutStore } from '../store/workoutStore'

type MessageType = 
  | 'USER_INPUT'
  | 'LOG_SET'
  | 'APPROVE_SUGGESTION'
  | 'RESUME'
  | 'FINISH_WORKOUT'

type ClientMessage = 
  | { type: 'USER_INPUT'; content: string; persona?: string; goal?: string }
  | { type: 'LOG_SET'; data: { exercise: string; weight: number; reps: number; rpe: number } }
  | { type: 'APPROVE_SUGGESTION'; approved: boolean }
  | { type: 'RESUME' }
  | { type: 'FINISH_WORKOUT' }
  | { type: 'RESET_USER' }
  | { type: 'RESET_FATIGUE' }
  | { type: 'RESET_WORKOUTS' }
  | { type: 'LOG_REST' }

type ServerMessage = 
  | { type: 'AGENT_RESPONSE'; state: any; workout: any; is_working_out?: boolean; workout_completed?: boolean; user_reset?: boolean }
  | { type: 'ERROR'; message: string }

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected'

export function useWorkoutSocket(userId: string) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const { setState, setWorkout, setIsWorkingOut, setError, clearState } = useWorkoutStore()

  const connect = () => {
    // Don't connect if no userId
    if (!userId || userId.trim() === '') {
      setConnectionStatus('disconnected')
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    setConnectionStatus('connecting')
    
    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_WS_HOST || window.location.hostname
    const port = import.meta.env.VITE_WS_PORT || (window.location.protocol === 'https:' ? '443' : '8000')
    const wsUrl = `${protocol}//${host}:${port}/ws/workout/${userId}`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setConnectionStatus('connected')
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
      }

      ws.onmessage = (event) => {
        try {
          const message: ServerMessage = JSON.parse(event.data)
          
          if (message.type === 'AGENT_RESPONSE') {
            // Update store with new state
            // If state is explicitly null, clear it (new user with no data)
            if (message.state === null) {
              setState(null)
              setWorkout(null)
              setIsWorkingOut(false)
            } else if (message.state) {
              setState(message.state)
            }
            // Always update workout - if it's None/null, clear it
            if (message.workout !== undefined) {
              setWorkout(message.workout || null)
            }
            if (message.is_working_out !== undefined) {
              setIsWorkingOut(message.is_working_out)
            }
            // Explicitly handle workout completion
            if (message.workout_completed) {
              setWorkout(null)
              setIsWorkingOut(false)
            }
            // Handle user reset
            if (message.user_reset) {
              setState(null)
              setWorkout(null)
              setIsWorkingOut(false)
            }
          } else if (message.type === 'ERROR') {
            console.error('WebSocket error:', message.message)
            setError(message.message)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus('disconnected')
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnectionStatus('disconnected')
        wsRef.current = null

        // Attempt to reconnect after 3 seconds
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null
            connect()
          }, 3000)
        }
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      setConnectionStatus('disconnected')
    }
  }

  const sendMessage = (message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message)
    }
  }

  useEffect(() => {
    // Close existing connection if userId changes
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    // Clear state immediately when userId changes (including when switching to null)
    clearState()

    if (userId && userId.trim() !== '') {
      // Small delay to ensure state is cleared before connecting
      const timeoutId = setTimeout(() => {
        connect()
      }, 100)
      return () => {
        clearTimeout(timeoutId)
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
        if (wsRef.current) {
          wsRef.current.close()
        }
      }
    } else {
      setConnectionStatus('disconnected')
      return () => {
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
        if (wsRef.current) {
          wsRef.current.close()
        }
      }
    }
  }, [userId])

  return {
    connectionStatus,
    sendMessage,
  }
}
