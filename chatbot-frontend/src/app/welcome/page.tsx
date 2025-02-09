'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline'

export default function WelcomePage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [message, setMessage] = useState('')
  const router = useRouter()
  const nickname = typeof window !== 'undefined' ? localStorage.getItem('nickname') : null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim()) {
      router.push(`/chat?message=${encodeURIComponent(message)}`)
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
          <div className="mt-8">
            <h3 className="text-lg font-semibold">Settings</h3>
            {/* Settings will go here */}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white shadow-sm">
          <div className="flex items-center p-4">
            <button onClick={() => setSidebarOpen(true)} className="mr-4">
              <Bars3Icon className="h-6 w-6" />
            </button>
            <h1 className="text-xl font-semibold">Welcome, {nickname || 'Guest'}</h1>
          </div>
        </header>

        <main className="flex-1 p-6 flex flex-col items-center justify-center">
          <div className="max-w-2xl w-full space-y-8">
            <div className="text-center">
              <h2 className="text-3xl font-bold">How can I help you today?</h2>
              <p className="mt-2 text-gray-600">Ask me anything!</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Type your message here..."
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Send Message
              </button>
            </form>
          </div>
        </main>
      </div>
    </div>
  )
}