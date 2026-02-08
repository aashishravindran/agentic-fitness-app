import { useEffect } from 'react'
import { motion } from 'framer-motion'
import MaxMascot from './MaxMascot'

interface GreetingBannerProps {
  message: string
  onComplete?: () => void
  autoAdvanceMs?: number
}

export default function GreetingBanner({
  message,
  onComplete,
  autoAdvanceMs = 3000,
}: GreetingBannerProps) {
  useEffect(() => {
    const t = setTimeout(() => {
      onComplete?.()
    }, autoAdvanceMs)
    return () => clearTimeout(t)
  }, [autoAdvanceMs, onComplete])

  if (!message) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="mb-6 p-4 bg-[#21262d] rounded-lg border border-[#00CFD1]/20"
    >
      <div className="flex gap-3">
        <MaxMascot size="lg" status="idle" animate />
        <div className="flex-1 min-w-0">
          <p className="text-gray-200 leading-relaxed">{message}</p>
        </div>
      </div>
    </motion.div>
  )
}
