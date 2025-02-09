'use client'

import React, { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useRouter, useSearchParams } from 'next/navigation'
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline'
import Message from './Message'
import ChatHistory from '@/components/ChatHistory'
import { Message as ChatMessage } from '@/types/chat'
import { sessionService } from '@/services/sessionService'

interface WebSocketMessage {
  type: 'message' | 'connection_status'
  message?: string
  formatted_message?: string
  sources?: string[]
  follow_up_questions?: string[]
}

export default function ChatPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const sessionId = searchParams.get('session')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isConnecting, setIsConnecting] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const ws = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 3

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const connectWebSocket = () => {
    try {
      if (!sessionId) return
      
      // Close existing connection if any
      if (ws.current) {
        ws.current.close(1000, 'Reconnecting')
      }

      ws.current = new WebSocket(`ws://localhost:8000/ws/${sessionId}`)

      ws.current.onopen = () => {
        console.log('WebSocket connected for session:', sessionId)
        setIsConnecting(false)
        setError(null)
        reconnectAttempts.current = 0
      }

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'message') {
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: data.message,
              sources: data.sources,
              follow_up_questions: data.follow_up_questions
            }])
            setIsLoading(false)
          }
        } catch (error) {
          console.error('Error parsing message:', error)
          setIsLoading(false)
        }
      }

      ws.current.onclose = (event) => {
        console.log('WebSocket closed:', event)
        setIsConnecting(true)
        
        // Attempt to reconnect if not closed intentionally
        if (!event.wasClean && reconnectAttempts.current < maxReconnectAttempts) {
          const timeout = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000)
          console.log(`Reconnecting in ${timeout}ms...`)
          
          setTimeout(() => {
            reconnectAttempts.current += 1
            connectWebSocket()
          }, timeout)
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError('Unable to connect to chat server. Please refresh the page.')
        }
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        // Don't set error immediately, let the onclose handler handle reconnection
        if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError('Connection error. Please check your internet connection and try again.')
        }
      }
    } catch (error) {
      console.error('Error setting up WebSocket:', error)
      setError('Failed to connect to chat server')
      setIsLoading(false)
    }
  }

  // Effect to handle session changes
  useEffect(() => {
    if (!sessionId) {
      router.push('/welcome')
      return
    }

    setError(null)
    reconnectAttempts.current = 0

    // Only load existing messages if we're viewing history
    // (messages array will already be populated for new chats)
    if (messages.length === 0) {
      const loadExistingMessages = async () => {
        try {
          const session = await sessionService.getSession(sessionId)
          if (session && session.messages) {
            setMessages(session.messages)
          }
        } catch (error) {
          console.error('Error loading messages:', error)
          setError('Failed to load chat history')
        }
      }
      loadExistingMessages()
    }

    connectWebSocket()

    return () => {
      if (ws.current) {
        ws.current.close(1000, 'Component unmounting or session changing')
      }
    }
  }, [sessionId, router, messages.length])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !ws.current || ws.current.readyState !== WebSocket.OPEN) return

    const newMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, newMessage])
    setInput('')
    setIsLoading(true)

    ws.current.send(JSON.stringify({
      user_id: localStorage.getItem('nickname'),
      user_input: input,
      session_id: sessionId
    }))
  }

  const renderMessage = (message: ChatMessage, index: number) => (
    <div key={index} 
         className={`mb-4 p-4 rounded-lg ${
           message.role === 'user' 
             ? 'bg-blue-600 ml-auto max-w-[80%]' 
             : 'bg-gray-800 mr-auto max-w-[80%]'
         }`}
    >
      <p className="text-white">{message.content}</p>
      {message.sources && message.sources.length > 0 && (
        <div className="mt-2 text-sm text-gray-300">
          <p className="font-semibold">Sources:</p>
          <ul className="list-disc list-inside">
            {message.sources.map((source, idx) => (
              <li key={idx}>{source}</li>
            ))}
          </ul>
        </div>
      )}
      {message.follow_up_questions && message.follow_up_questions.length > 0 && (
        <div className="mt-2">
          <p className="text-sm font-semibold text-gray-300">Follow-up questions:</p>
          <div className="flex flex-wrap gap-2 mt-1">
            {message.follow_up_questions.map((question, idx) => (
              <button
                key={idx}
                className="text-sm px-3 py-1 rounded-full bg-gray-700 text-gray-300 hover:bg-gray-600"
                onClick={() => {/* Handle follow-up question */}}
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-900">
      <ChatHistory isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <div className="flex flex-col h-screen">
        {/* Header */}
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

        {/* Error Banner */}
        {error && (
          <div className="bg-red-500 text-white px-4 py-2">
            <p>{error}</p>
            <button 
              onClick={() => {
                setError(null)
                reconnectAttempts.current = 0
                connectWebSocket()
              }}
              className="text-sm underline hover:no-underline ml-2"
            >
              Try again
            </button>
          </div>
        )}

        {/* Chat content */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex justify-center items-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
            </div>
          ) : (
            messages.map((message, index) => renderMessage(message, index))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-gray-800">
          <div className="max-w-4xl mx-auto flex gap-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 p-2 bg-gray-800 border border-gray-700 rounded-lg 
                       text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className={`px-4 py-2 rounded-lg text-white font-medium
                       ${isLoading || !input.trim() 
                         ? 'bg-gray-600 cursor-not-allowed' 
                         : 'bg-blue-600 hover:bg-blue-700'}`}
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}