import Layout from '../components/Layout'
import { useEffect, useState } from 'react'
import { fetchSystem } from '../lib/api'
import { getToken } from '../lib/auth'
import { useRouter } from 'next/router'

export default function SystemPage(){
  const [data, setData] = useState(null)
  const router = useRouter()
  useEffect(()=>{
    if(!getToken()) { router.push('/login'); return }
    const load = async () => { try { setData(await fetchSystem()) } catch(e){ if(e.response?.status===401) router.push('/login') } }
    load()
    const id = setInterval(load, 15000)
    return ()=> clearInterval(id)
  },[])
  if(!data) return <div>Loading...</div>
  return <Layout>
    <h1 className="text-xl font-semibold mb-4">System Metrics</h1>
    <pre className="bg-gray-800 p-4 rounded text-sm overflow-x-auto">{JSON.stringify(data,null,2)}</pre>
  </Layout>
}
