import { useEffect, useState } from 'react'
import { getToken, clearToken } from '../lib/auth'
import { useRouter } from 'next/router'

export default function Topbar() {
  const [time, setTime] = useState(new Date())
  const router = useRouter()
  useEffect(() => {
    const id = setInterval(()=> setTime(new Date()), 1000)
    return ()=> clearInterval(id)
  }, [])
  return (
    <header className="flex items-center justify-between px-4 py-2 bg-gray-850 border-b border-gray-700">
      <div className="text-sm text-gray-400">Last update: {time.toLocaleTimeString()}</div>
      <button onClick={() => { clearToken(); router.push('/login')}} className="text-sm bg-red-600 hover:bg-red-500 px-3 py-1 rounded">Logout</button>
    </header>
  )
}
