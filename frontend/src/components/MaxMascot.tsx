import { motion } from 'framer-motion'

type Status = 'idle' | 'thinking' | 'success'

interface MaxMascotProps {
  className?: string
  status?: Status
  animate?: boolean
  size?: 'sm' | 'md' | 'lg'
}

const sizeMap = {
  sm: 'w-8 h-8',
  md: 'w-12 h-12',
  lg: 'w-16 h-16',
}

export default function MaxMascot({
  className = 'w-16 h-16',
  status = 'idle',
  animate = false,
  size,
}: MaxMascotProps) {
  const sizeClass = size ? sizeMap[size] : null
  const svg = (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={sizeClass || className}
      aria-hidden
    >
      {/* Floating Shadow */}
      <ellipse cx="50" cy="90" rx="20" ry="5" fill="black" fillOpacity="0.1" />

      {/* Body / Torso */}
      <path
        d="M35 55C35 52.2386 37.2386 50 40 50H60C62.7614 50 65 52.2386 65 55V65C65 73.2843 58.2843 80 50 80C41.7157 80 35 73.2843 35 65V55Z"
        fill="#F8FAFC"
      />
      <circle cx="50" cy="65" r="6" fill="#00CFD1" fillOpacity="0.3" />
      <circle cx="50" cy="65" r="3" fill="#00CFD1" />

      {/* Head */}
      <rect x="25" y="15" width="50" height="40" rx="15" fill="#F8FAFC" />

      {/* Face Screen */}
      <rect x="30" y="20" width="40" height="25" rx="8" fill="#1A202C" />

      {/* Digital Eyes (Teal) - expression based on status */}
      {status === 'thinking' && (
        <path
          d="M 12,30 A 8,8 0 1,1 28,30 M 52,30 A 8,8 0 1,1 68,30"
          stroke="#00CFD1"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
        />
      )}
      {status === 'success' && (
        <g stroke="#00CFD1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none">
          <path d="M 38,25 L 42,29 L 48,23" />
          <path d="M 52,25 L 56,29 L 62,23" />
        </g>
      )}
      {status === 'idle' && (
        <g stroke="#00CFD1" fill="#00CFD1">
          <circle cx="42" cy="30" r="2.5" />
          <circle cx="58" cy="30" r="2.5" />
        </g>
      )}

      {/* Mouth */}
      <path d="M45 38H55" stroke="#00CFD1" strokeWidth="2" strokeLinecap="round" />

      {/* Antennas */}
      <line x1="40" y1="15" x2="35" y2="8" stroke="#F8FAFC" strokeWidth="2" />
      <circle cx="35" cy="8" r="2" fill="#00CFD1" />
      <line x1="60" y1="15" x2="65" y2="8" stroke="#F8FAFC" strokeWidth="2" />
      <circle cx="65" cy="8" r="2" fill="#00CFD1" />
    </svg>
  )

  if (animate) {
    return (
      <motion.div
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        className="shrink-0"
      >
        {svg}
      </motion.div>
    )
  }

  return <div className="shrink-0">{svg}</div>
}
