'use client'

import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'next/navigation'
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline'

interface Message {
  type: 'user' | 'bot' | 'error'
  content: string
  sources?: string[]
  follow_up_questions?: string[]
  timestamp: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const searchParams = useSearchParams()
  const wsRef = useRef<WebSocket | null>(null)
  const sessionId = useRef<string>(crypto.randomUUID())
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId.current}`)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      setError(null)
      console.log('WebSocket Connected')
      
      const initialMessage = searchParams.get('message')
      if (initialMessage) {
        sendMessage(initialMessage)
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log("Received WebSocket data:", data) // Debug log
        if (data.type === "connection_status") {
          console.log("Connection status:", data.content)
          return
        }
        setMessages(prev => [...prev, {
          type: 'bot',
          content: data.message,
          sources: data.sources || [],
          follow_up_questions: data.follow_up_questions || [],
          timestamp: new Date().toISOString()
        }])
      } catch (error) {
        console.error('Error parsing message:', error)
        setMessages(prev => [...prev, {
          type: 'error',
          content: 'Error processing response',
          timestamp: new Date().toISOString()
        }])
      }
    }

    ws.onerror = () => {
      const errorMessage = 'Connection error. Please try again.'
      setError(errorMessage)
      setIsConnected(false)
    }

    ws.onclose = () => {
      const closeMessage = 'Connection closed. Please refresh the page.'
      setIsConnected(false)
      setError(closeMessage)
    }

    return () => {
      ws.close()
    }
  }, [searchParams])

  const handleFollowUpClick = (question: string) => {
    console.log("Follow-up question clicked:", question) // Debug log
    setInput(question)
    sendMessage(question)
  }

  const sendMessage = async (messageContent: string) => {
    try {
      if (!isConnected) {
        throw new Error('Unable to connect to chat service')
      }

      setMessages(prev => [...prev, {
        type: 'user',
        content: messageContent,
        timestamp: new Date().toISOString()
      }])

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          user_id: localStorage.getItem('nickname') || 'anonymous',
          user_input: messageContent,
          session_id: sessionId.current
        }))
        setInput('')
      } else {
        throw new Error('Chat service connection lost. Please refresh the page.')
      }
    } catch (error) {
      const userFriendlyError = error instanceof Error 
        ? error.message 
        : 'Something went wrong. Please try again.'
      setError(userFriendlyError)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) {
      sendMessage(input)
    }
  }

  return (
    <div className="h-screen flex">
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} w-64 bg-white shadow-lg transition-transform duration-300 ease-in-out z-20`}>
        <div className="p-4">
          <button onClick={() => setSidebarOpen(false)} className="float-right">
            <XMarkIcon className="h-6 w-6" />
          </button>
          <div className="mt-8">
            <h3 className="text-lg font-semibold">Chat History</h3>
            {/* Chat history will go here */}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="flex items-center p-4">
            <button onClick={() => setSidebarOpen(true)} className="mr-4">
              <Bars3Icon className="h-6 w-6" />
            </button>
            <h1 className="text-xl font-semibold">Chat</h1>
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-50 p-4 border-l-4 border-red-400">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[70%] ${message.type === 'user' ? 'items-end' : 'items-start'}`}>
                {/* Message Content */}
                <div className={`rounded-lg p-3 ${
                  message.type === 'user'
                    ? 'bg-blue-500 text-white'
                    : message.type === 'error'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-gray-200 text-gray-800'
                }`}>
                  {message.content}
                </div>

                {/* Sources */}
                {message.type === 'bot' && message.sources && message.sources.length > 0 && (
                  <div className="text-sm text-gray-600 mt-2">
                    <div className="font-semibold mb-1">Sources:</div>
                    {message.sources.map((source, idx) => (
                      <div key={idx} className="ml-2">• {source}</div>
                    ))}
                  </div>
                )}

                {/* Follow-up Questions */}
                {message.type === 'bot' && message.follow_up_questions && message.follow_up_questions.length > 0 && (
                  <div className="text-sm mt-4">
                    <div className="font-semibold mb-2">Suggested Questions:</div>
                    <div className="flex flex-col gap-2">
                      {message.follow_up_questions.map((question, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleFollowUpClick(question)}
                          className="text-left text-blue-600 hover:text-blue-800 hover:underline ml-2 py-1 px-2 rounded cursor-pointer"
                        >
                          • {question}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="border-t p-4">
          <div className="flex space-x-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              disabled={!isConnected}
            />
            <button
              type="submit"
              disabled={!isConnected}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}