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
    <div className="mb-6 p-4 bg-yellow-50 border-2 border-yellow-300 rounded-lg shadow-md">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <div className="w-8 h-8 bg-yellow-400 rounded-full flex items-center justify-center">
            <span className="text-yellow-900 font-bold">!</span>
          </div>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-yellow-900 mb-1">Coach Suggestion</h3>
          <p className="text-sm text-yellow-800 mb-3">{message}</p>
          <div className="flex gap-2">
            <button
              onClick={onApprove}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-medium"
            >
              Accept
            </button>
            <button
              onClick={onIgnore}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 text-sm font-medium"
            >
              Ignore
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
