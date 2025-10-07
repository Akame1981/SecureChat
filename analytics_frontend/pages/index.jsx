import Layout from '../components/Layout'
import { useEffect, useState } from 'react'
import { fetchSystem, fetchUsers, fetchMessages } from '../lib/api'
import { getToken } from '../lib/auth'
import { useRouter } from 'next/router'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'

export default function Overview(){
  const [system, setSystem] = useState(null)
  const [users, setUsers] = useState(null)
  const [messages, setMessages] = useState(null)
  const router = useRouter()
  const [intervalSec, setIntervalSec] = useState(15)

  useEffect(()=>{
    if(!getToken()) { router.push('/login'); return }
    const load = async () => {
      try {
        setSystem(await fetchSystem())
        setUsers(await fetchUsers())
        setMessages(await fetchMessages())
      } catch(e){
        if(e.response && e.response.status === 401) router.push('/login')
      }
    }
    load()
    const id = setInterval(load, intervalSec * 1000)
    return ()=> clearInterval(id)
  }, [intervalSec])

  if(!system || !users || !messages) return <div className="p-4 text-gray-400">Loading...</div>

  const dayDistribution = messages.per_day.map(d => ({ name: d.day, value: d.messages }))
  const colors = ['#6366f1','#8b5cf6','#ec4899','#10b981','#f59e0b','#ef4444','#3b82f6']

  return (
    <Layout>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard title="CPU %" value={system.cpu.toFixed(1)} />
        <MetricCard title="Mem %" value={system.memory.toFixed(1)} />
        <MetricCard title="Disk %" value={system.disk.toFixed(1)} />
        <MetricCard title="Active Users" value={users.active_users} />
        <MetricCard title="Total Users" value={users.total_users} />
        <MetricCard title="Messages Today" value={messages.messages_today} />
        <MetricCard title="Avg Msg Size" value={messages.avg_message_size.toFixed(1)} />
        <div className="bg-gray-800 rounded p-4 flex flex-col">
          <label className="text-xs text-gray-400 mb-1">Refresh Interval (s)</label>
          <input type="number" min={10} max={60} value={intervalSec} onChange={e=>setIntervalSec(Number(e.target.value))} className="bg-gray-700 rounded px-2 py-1 text-sm" />
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-4 rounded h-80">
          <h2 className="text-sm mb-2 font-semibold">Messages per Hour</h2>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={messages.per_hour}>
              <XAxis dataKey="hour" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip />
              <Line type="monotone" dataKey="messages" stroke="#6366f1" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-gray-800 p-4 rounded h-80">
          <h2 className="text-sm mb-2 font-semibold">Daily Distribution</h2>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={dayDistribution} dataKey="value" nameKey="name" outerRadius={100} label>
                {dayDistribution.map((entry, idx) => (
                  <Cell key={idx} fill={colors[idx % colors.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Layout>
  )
}

function MetricCard({title, value}) {
  return (
    <div className="bg-gray-800 rounded p-4">
      <div className="text-xs uppercase tracking-wide text-gray-400 mb-1">{title}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  )
}
