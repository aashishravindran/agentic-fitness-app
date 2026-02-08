import MaxMascot from './MaxMascot'

interface NavbarProps {
  userId: string
  onSwitchUser: () => void
  onViewHistory?: () => void
  connectionStatus: 'connected' | 'connecting' | 'disconnected'
}

export default function Navbar({ userId, onSwitchUser, onViewHistory, connectionStatus }: NavbarProps) {
  return (
    <nav className="sticky top-0 z-40 bg-[#0D1117]/95 backdrop-blur border-b border-[#00CFD1]/20">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between max-w-4xl">
        <h1 className="text-xl font-bold text-[#00CFD1]">SuperSet</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              connectionStatus === 'connected' ? 'bg-[#00CFD1]' :
              connectionStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' :
              'bg-red-500'
            }`} />
            <span className="text-sm text-gray-400">
              {connectionStatus === 'connected' ? 'Connected' :
               connectionStatus === 'connecting' ? 'Connecting...' :
               'Disconnected'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">
              Logged in as <span className="font-semibold text-[#00CFD1]">{userId}</span>
            </span>
            {onViewHistory && (
              <button onClick={onViewHistory} className="text-sm text-gray-400 hover:text-[#00CFD1] hover:underline">
                Past workouts
              </button>
            )}
            <button
              onClick={onSwitchUser}
              className="text-sm text-[#00CFD1] hover:text-[#00e5e7] hover:underline"
            >
              Switch User
            </button>
          </div>
          <MaxMascot size="sm" />
        </div>
      </div>
    </nav>
  )
}
