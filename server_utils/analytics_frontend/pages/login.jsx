import { useState } from 'react'
import { login } from '../lib/api'
import { setToken } from '../lib/auth'
import { useRouter } from 'next/router'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const router = useRouter()

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const data = await login(username, password)
      setToken(data.access_token)
      router.push('/')
    } catch (e) {
      setError('Invalid credentials')
    }
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-900">
      <form onSubmit={submit} className="bg-gray-800 p-8 rounded space-y-4 w-80">
        <h1 className="text-xl font-semibold">Admin Login</h1>
        {error && <div className="text-red-500 text-sm">{error}</div>}
        <input value={username} onChange={e=>setUsername(e.target.value)} placeholder="Username" className="w-full px-3 py-2 rounded bg-gray-700 focus:outline-none" />
        <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" className="w-full px-3 py-2 rounded bg-gray-700 focus:outline-none" />
        <button className="w-full bg-blue-600 hover:bg-blue-500 py-2 rounded">Login</button>
      </form>
    </div>
  )
}
