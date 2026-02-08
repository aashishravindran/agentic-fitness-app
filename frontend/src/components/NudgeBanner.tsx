interface NudgeBannerProps {
  message: string
  onApprove: () => void
  onIgnore: () => void
}

export default function NudgeBanner({ message, onApprove, onIgnore }: NudgeBannerProps) {
  // Only show if message contains suggestions or recommendations
  const isNudge = message.toLowerCase().includes('suggest') || 
                  message.toLowerCase().includes('recommend') ||
                  message.toLowerCase().includes('consider') ||
                  message.toLowerCase().includes('drop') ||
                  message.toLowerCase().includes('reduce')

  if (!isNudge || !message) {
    return null
  }

  return (
    <div className="mb-6 p-4 bg-[#21262d] border-2 border-[#00CFD1]/50 rounded-lg">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <div className="w-8 h-8 bg-[#00CFD1] rounded-full flex items-center justify-center">
            <span className="text-[#0D1117] font-bold">!</span>
          </div>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-[#00CFD1] mb-1">Max Suggestion</h3>
          <p className="text-sm text-gray-300 mb-3">{message}</p>
          <div className="flex gap-2">
            <button
              onClick={onApprove}
              className="px-4 py-2 bg-[#00CFD1] text-[#0D1117] rounded-md hover:bg-[#00e5e7] text-sm font-medium"
            >
              Accept
            </button>
            <button
              onClick={onIgnore}
              className="px-4 py-2 bg-gray-600 text-gray-300 rounded-md hover:bg-gray-500 text-sm font-medium"
            >
              Ignore
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
