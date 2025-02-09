'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

// This is your root page (login)
export default function LoginPage() {
  const [nickname, setNickname] = useState('')
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    const finalNickname = nickname || `user_${Math.random().toString(36).slice(2, 7)}`
    localStorage.setItem('nickname', finalNickname)
    router.push('/welcome')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-xl shadow-lg">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">Welcome to AI Chat</h2>
          <p className="mt-2 text-gray-600">Enter a nickname or continue as guest</p>
        </div>
        
        <form onSubmit={handleLogin} className="mt-8 space-y-6">
          <input
            type="text"
            placeholder="Enter nickname (optional)"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          
          <button
            type="submit"
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Start Chatting
          </button>
        </form>
      </div>
    </div>
  )
}