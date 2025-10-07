import Layout from '../components/Layout'
import { useEffect, useState } from 'react'
import { fetchUsers } from '../lib/api'
import { getToken } from '../lib/auth'
import { useRouter } from 'next/router'

export default function UsersPage(){
  const [data, setData] = useState(null)
  const router = useRouter()
  useEffect(()=>{
    if(!getToken()) { router.push('/login'); return }
    const load = async () => { try { setData(await fetchUsers()) } catch(e){ if(e.response?.status===401) router.push('/login') } }
    load()
    const id = setInterval(load, 20000)
    return ()=> clearInterval(id)
  },[])
  if(!data) return <div>Loading...</div>
  return <Layout>
    <h1 className="text-xl font-semibold mb-4">User Metrics</h1>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Metric title="Total Users" value={data.total_users} />
      <Metric title="Active Users" value={data.active_users} />
      <Metric title="New Today" value={data.new_users_today} />
    </div>
    <pre className="bg-gray-800 p-4 rounded text-sm overflow-x-auto">{JSON.stringify(data,null,2)}</pre>
  </Layout>
}

function Metric({title,value}){return <div className="bg-gray-800 p-4 rounded"><div className="text-xs text-gray-400 mb-1">{title}</div><div className="text-2xl font-semibold">{value}</div></div>}
