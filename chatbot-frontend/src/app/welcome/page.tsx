'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import ChatHistory from '@/components/ChatHistory'

export default function WelcomePage() {
  const router = useRouter()
  const [nickname, setNickname] = useState('')
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const storedNickname = localStorage.getItem('nickname')
    if (!storedNickname) {
      router.push('/')
    } else {
      setNickname(storedNickname)
    }
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return

    setIsLoading(true)
    try {
      const sessionId = crypto.randomUUID()
      const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`)
      
      await new Promise((resolve, reject) => {
        ws.onopen = resolve
        ws.onerror = reject
      })

      ws.send(JSON.stringify({
        user_id: nickname,
        user_input: question,
        session_id: sessionId,
        type: 'message'
      }))

      ws.close()
      router.push(`/chat?session=${sessionId}`)
    } catch (error) {
      console.error('Error starting chat:', error)
      alert('Failed to start chat. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <ChatHistory isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <div className="flex flex-col h-screen">
        <header className="bg-gray-800 shadow">
          <div className="flex items-center p-4">
            <button 
              onClick={() => setSidebarOpen(true)}
              className="text-gray-300 hover:text-white"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </header>

        <main className="flex-1 flex items-center justify-center p-4">
          <div className="max-w-2xl w-full">
            <h1 className="text-4xl font-bold text-white text-center mb-8">
              How can I help you today?
            </h1>
            <p className="text-gray-400 text-center mb-8">
              Ask me anything!
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="question" className="sr-only">
                  What would you like to know?
                </label>
                <textarea
                  id="question"
                  rows={4}
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg 
                           text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500 
                           focus:border-transparent resize-none"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask me anything..."
                  disabled={isLoading}
                />
              </div>
              <button
                type="submit"
                disabled={isLoading || !question.trim()}
                className={`w-full py-3 px-4 rounded-lg text-white font-medium
                         ${isLoading || !question.trim() 
                           ? 'bg-gray-600 cursor-not-allowed' 
                           : 'bg-blue-600 hover:bg-blue-700'} 
                         transition-colors duration-200`}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" 
                         xmlns="http://www.w3.org/2000/svg" 
                         fill="none" 
                         viewBox="0 0 24 24"
                    >
                      <circle className="opacity-25" cx="12" cy="12" r="10" 
                              stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" 
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Starting Chat...
                  </span>
                ) : (
                  'Start Chat'
                )}
              </button>
            </form>
          </div>
        </main>
      </div>
    </div>
  )
}