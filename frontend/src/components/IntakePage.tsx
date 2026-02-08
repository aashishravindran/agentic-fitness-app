import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import MaxMascot from './MaxMascot'

type Step = 'welcome' | 'height' | 'weight' | 'fitness' | 'about' | 'complete'

interface Message {
  id: string
  sender: 'max' | 'user'
  text: string
}

interface IntakePageProps {
  userId: string
  onComplete: () => void
}

const STEPS: Record<Exclude<Step, 'complete'>, { text: string; type?: 'number' | 'text'; placeholder?: string }> = {
  welcome: { text: "Hi! I'm Max. I'm here to optimize your training stack. Ready to start your first Quest?" },
  height: { text: "First, let's get the biometrics. What's your height in cm?", type: 'number', placeholder: 'e.g. 175' },
  weight: { text: "And your current weight in kg?", type: 'number', placeholder: 'e.g. 75' },
  fitness: { text: "How would you describe your fitness level? (Beginner, Intermediate, or Advanced)", type: 'text' },
  about: {
    text: "Final step: Tell me something interesting! Your job, a trip you're planning, or physical notes like 'sensitive knees'. I'll use this to optimize your logic.",
    type: 'text',
    placeholder: "e.g. SDE at AWS, planning a Zion trip, sensitive knees...",
  },
}

export default function IntakePage({ userId, onComplete }: IntakePageProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [step, setStep] = useState<Step>('welcome')
  const [height, setHeight] = useState('')
  const [weight, setWeight] = useState('')
  const [fitnessLevel, setFitnessLevel] = useState('Intermediate')
  const [aboutMe, setAboutMe] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addMessage = (text: string, sender: 'max' | 'user') => {
    setMessages((prev) => [...prev, { id: Date.now().toString(), sender, text }])
  }

  const handleNext = async () => {
    if (step === 'welcome') {
      addMessage("Let's go!", 'user')
      setIsTyping(true)
      setStep('height')
      setTimeout(() => {
        addMessage(STEPS.height.text, 'max')
        setIsTyping(false)
      }, 800)
      return
    }

    if (step === 'height') {
      const h = parseFloat(inputValue || height)
      if (isNaN(h) || h < 100 || h > 250) {
        setError('Enter a valid height (100–250 cm)')
        return
      }
      setHeight(String(h))
      addMessage(`${h} cm`, 'user')
      setInputValue('')
      setError(null)
      setIsTyping(true)
      setStep('weight')
      setTimeout(() => {
        addMessage(STEPS.weight.text, 'max')
        setIsTyping(false)
      }, 600)
      return
    }

    if (step === 'weight') {
      const w = parseFloat(inputValue || weight)
      if (isNaN(w) || w < 30 || w > 300) {
        setError('Enter a valid weight (30–300 kg)')
        return
      }
      setWeight(String(w))
      addMessage(`${w} kg`, 'user')
      setInputValue('')
      setError(null)
      setIsTyping(true)
      setStep('fitness')
      setTimeout(() => {
        addMessage(STEPS.fitness.text, 'max')
        setIsTyping(false)
      }, 600)
      return
    }

    if (step === 'fitness') {
      const level = inputValue || fitnessLevel
      setFitnessLevel(level)
      addMessage(level, 'user')
      setInputValue('')
      setIsTyping(true)
      setStep('about')
      setTimeout(() => {
        addMessage(STEPS.about.text, 'max')
        setIsTyping(false)
      }, 600)
      return
    }

    if (step === 'about') {
      const text = inputValue || aboutMe
      setAboutMe(text)
      addMessage(text || '(skipped)', 'user')
      setInputValue('')
      setLoading(true)
      setError(null)
      const base = `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${import.meta.env.VITE_WS_HOST || window.location.hostname}:${import.meta.env.VITE_WS_PORT || (window.location.protocol === 'https:' ? '443' : '8000')}`
      try {
        const res = await fetch(`${base}/api/users/${encodeURIComponent(userId)}/intake`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            height_cm: parseFloat(height),
            weight_kg: parseFloat(weight),
            fitness_level: fitnessLevel,
            about_me: (text || aboutMe).trim() || '',
          }),
        })
        if (!res.ok) throw new Error(res.status === 409 ? 'Already onboarded' : 'Failed to complete intake')
        setStep('complete')
        setIsTyping(true)
        setTimeout(() => {
          addMessage("Perfect. I've initialized your profile. Let's head to the Dashboard!", 'max')
          setIsTyping(false)
        }, 600)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed')
      } finally {
        setLoading(false)
      }
      return
    }

    if (step === 'complete') {
      onComplete()
    }
  }

  useEffect(() => {
    if (step === 'welcome') {
      setIsTyping(true)
      setTimeout(() => {
        addMessage(STEPS.welcome.text, 'max')
        setIsTyping(false)
      }, 500)
    }
  }, [])

  const isDisabled =
    loading ||
    (step === 'height' && !inputValue && !height) ||
    (step === 'weight' && !inputValue && !weight)
  const buttonLabel = loading ? 'Saving...' : step === 'complete' ? "Let's go" : step === 'welcome' ? "Let's Go" : 'Next'

  return (
    <div className="min-h-screen bg-[#0D1117] text-white flex flex-col p-6 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-[#00CFD1]">SuperSet</h1>
        <div className="text-xs uppercase tracking-widest text-gray-500">Intake Quest</div>
      </div>

      {/* Chat Window */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-6">
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${msg.sender === 'max' ? 'justify-start' : 'justify-end'}`}
            >
              <div
                className={`flex gap-3 max-w-[85%] ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}
              >
                {msg.sender === 'max' && <MaxMascot size="sm" className="shrink-0" />}
                <div
                  className={`px-4 py-3 rounded-2xl ${
                    msg.sender === 'max'
                      ? 'bg-[#21262d] text-gray-200 rounded-tl-none border-l-4 border-[#00CFD1]'
                      : 'bg-[#00CFD1] text-[#0D1117] font-semibold rounded-tr-none'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            </motion.div>
          ))}
          {isTyping && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-3"
            >
              <MaxMascot size="sm" className="shrink-0" status={isTyping ? 'thinking' : 'idle'} />
              <div className="text-[#00CFD1] text-sm italic px-4 py-2">Max is thinking...</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Area */}
      {step !== 'complete' && (
        <div className="space-y-2">
          {step === 'height' && (
            <input
              autoFocus
              type="number"
              value={inputValue || height}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleNext()}
              placeholder={STEPS.height.placeholder}
              className="w-full px-4 py-3 bg-[#161B22] border border-gray-600 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-[#00CFD1] transition-colors"
            />
          )}
          {step === 'weight' && (
            <input
              autoFocus
              type="number"
              value={inputValue || weight}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleNext()}
              placeholder={STEPS.weight.placeholder}
              className="w-full px-4 py-3 bg-[#161B22] border border-gray-600 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-[#00CFD1] transition-colors"
            />
          )}
          {step === 'fitness' && (
            <select
              value={inputValue || fitnessLevel}
              onChange={(e) => setInputValue(e.target.value)}
              className="w-full px-4 py-3 bg-[#161B22] border border-gray-600 rounded-xl text-white focus:outline-none focus:border-[#00CFD1]"
            >
              <option value="Beginner">Beginner</option>
              <option value="Intermediate">Intermediate</option>
              <option value="Advanced">Advanced</option>
            </select>
          )}
          {step === 'about' && (
            <textarea
              value={inputValue || aboutMe}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={STEPS.about.placeholder}
              rows={3}
              className="w-full px-4 py-3 bg-[#161B22] border border-gray-600 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-[#00CFD1] resize-none"
              autoFocus
            />
          )}
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            onClick={handleNext}
            disabled={isDisabled}
            className="w-full px-6 py-3 bg-[#00CFD1] text-[#0D1117] font-bold rounded-xl hover:bg-[#00e5e8] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {buttonLabel}
          </button>
        </div>
      )}

      {step === 'complete' && (
        <button
          onClick={handleNext}
          className="w-full px-6 py-3 bg-[#00CFD1] text-[#0D1117] font-bold rounded-xl hover:bg-[#00e5e8] transition-colors"
        >
          Let's go
        </button>
      )}
    </div>
  )
}
