import Layout from '../components/Layout'
import { getToken, clearToken } from '../lib/auth'
import { useRouter } from 'next/router'
import { useEffect } from 'react'

export default function SettingsPage(){
  const router = useRouter()
  useEffect(()=>{ if(!getToken()) router.push('/login') },[])
  return <Layout>
    <h1 className="text-xl font-semibold mb-4">Settings</h1>
    <button onClick={()=>{clearToken(); router.push('/login')}} className="bg-red-600 hover:bg-red-500 px-4 py-2 rounded">Logout</button>
    <p className="mt-6 text-sm text-gray-400">Additional admin settings can go here.</p>
  </Layout>
}
