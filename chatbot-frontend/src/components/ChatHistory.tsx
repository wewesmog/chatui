'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Session, GroupedSessions } from '@/types/chat'
import { sessionService } from '@/services/sessionService'

interface ChatHistoryProps {
  isOpen: boolean
  onClose: () => void
}

export default function ChatHistory({ isOpen, onClose }: ChatHistoryProps) {
  const router = useRouter()
  const [sessions, setSessions] = useState<GroupedSessions>({
    today: [],
    thisWeek: [],
    thisMonth: [],
    older: []
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadSessions = async () => {
      try {
        const allSessions = await sessionService.getSessions()
        const grouped = groupSessionsByDate(allSessions)
        setSessions(grouped)
      } catch (error) {
        console.error('Error loading sessions:', error)
        setError('Failed to load chat history')
      } finally {
        setIsLoading(false)
      }
    }

    loadSessions()
  }, [])

  const groupSessionsByDate = (sessions: Session[]) => {
    const now = new Date()
    const today = new Date(now.setHours(0, 0, 0, 0))
    const thisWeek = new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000)
    const thisMonth = new Date(today.getTime() - 29 * 24 * 60 * 60 * 1000)

    return sessions.reduce((groups, session) => {
      const sessionDate = new Date(session.timestamp)
      if (sessionDate >= today) {
        groups.today.push(session)
      } else if (sessionDate >= thisWeek) {
        groups.thisWeek.push(session)
      } else if (sessionDate >= thisMonth) {
        groups.thisMonth.push(session)
      } else {
        groups.older.push(session)
      }
      return groups
    }, {
      today: [] as Session[],
      thisWeek: [] as Session[],
      thisMonth: [] as Session[],
      older: [] as Session[]
    })
  }

  const renderSessionGroup = (title: string, sessions: Session[]) => {
    if (sessions.length === 0) return null

    return (
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-400 mb-2">{title}</h3>
        <div className="space-y-2">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => {
                router.push(`/chat?session=${session.id}`)
                onClose()
              }}
              className="w-full text-left p-3 rounded-lg bg-gray-800 hover:bg-gray-700 
                       transition-colors duration-200"
            >
              <p className="text-sm text-gray-300 line-clamp-2">
                {session.first_message}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {formatDate(session.timestamp)}
              </p>
            </button>
          ))}
        </div>
      </div>
    )
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div 
      className={`fixed inset-y-0 left-0 w-80 bg-gray-900 transform ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      } transition-transform duration-300 ease-in-out z-50`}
    >
      <div className="h-full flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-white">Chat History</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors duration-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex justify-center items-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          ) : error ? (
            <div className="p-4 text-sm text-red-400 bg-red-900/10 rounded-lg">
              {error}
              <button 
                onClick={() => window.location.reload()}
                className="mt-2 text-blue-400 hover:text-blue-300"
              >
                Try again
              </button>
            </div>
          ) : Object.values(sessions).every(group => group.length === 0) ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-500">
              <p className="text-sm">No chat history yet</p>
              <p className="text-xs mt-1">Start a new chat to see it here</p>
            </div>
          ) : (
            <>
              {renderSessionGroup('Today', sessions.today)}
              {renderSessionGroup('This Week', sessions.thisWeek)}
              {renderSessionGroup('This Month', sessions.thisMonth)}
              {renderSessionGroup('Older', sessions.older)}
            </>
          )}
        </div>
      </div>
    </div>
  )
}