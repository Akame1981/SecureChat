import Layout from '../components/Layout'
import { useEffect, useState } from 'react'
import { fetchMessages } from '../lib/api'
import { getToken } from '../lib/auth'
import { useRouter } from 'next/router'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function MessagesPage(){
  const [data, setData] = useState(null)
  const router = useRouter()
  useEffect(()=>{
    if(!getToken()) { router.push('/login'); return }
    const load = async () => { try { setData(await fetchMessages()) } catch(e){ if(e.response?.status===401) router.push('/login') } }
    load()
    const id = setInterval(load, 20000)
    return ()=> clearInterval(id)
  },[])
  if(!data) return <div>Loading...</div>
  return <Layout>
    <h1 className="text-xl font-semibold mb-4">Message Metrics</h1>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Metric title="Messages Today" value={data.messages_today} />
      <Metric title="Avg Size" value={data.avg_message_size.toFixed(1)} />
    </div>
    <div className="bg-gray-800 p-4 rounded h-80 mb-6">
      <h2 className="text-sm mb-2 font-semibold">Per Hour</h2>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data.per_hour}>
          <XAxis dataKey="hour" stroke="#9ca3af" />
          <YAxis stroke="#9ca3af" />
          <Tooltip />
          <Line type="monotone" dataKey="messages" stroke="#10b981" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
    <pre className="bg-gray-800 p-4 rounded text-sm overflow-x-auto">{JSON.stringify(data,null,2)}</pre>
  </Layout>
}

function Metric({title,value}){return <div className="bg-gray-800 p-4 rounded"><div className="text-xs text-gray-400 mb-1">{title}</div><div className="text-2xl font-semibold">{value}</div></div>}
