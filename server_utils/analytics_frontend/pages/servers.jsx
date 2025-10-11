import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import { fetchPublicServers, deleteGroup } from '../lib/servers'
import { useRouter } from 'next/router'

export default function ServersPage(){
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const load = async (query) => {
    setLoading(true)
    try{
      const res = await fetchPublicServers(query)
      setItems(res.groups || [])
    }catch(e){
      console.error(e)
      setItems([])
    }finally{ setLoading(false) }
  }

  useEffect(()=>{ load(null) }, [])

  const onSearch = async () => { load(q || null) }

  const onDelete = async (id) => {
    if(!confirm('Delete group permanently? This cannot be undone.')) return
    try{
      await deleteGroup(id)
      // reload
      load(q || null)
    }catch(e){
      console.error('Delete error:', e)
      let msg = 'Delete failed'
      try{
        if(e?.response?.data) msg = JSON.stringify(e.response.data)
        else if(e?.message) msg = e.message
        else msg = String(e)
      }catch(_){ msg = String(e) }
      alert(msg)
    }
  }

  return (
    <Layout>
      <div style={{padding:20}}>
        <h2>Public Servers</h2>
        <div style={{marginBottom:12}}>
          <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search by name" style={{padding:8, width:300}} />
          <button onClick={onSearch} style={{marginLeft:8}}>Search</button>
        </div>
        {loading ? <div>Loading…</div> : (
          <table style={{width:'100%', borderCollapse:'collapse'}}>
            <thead>
              <tr style={{textAlign:'left'}}>
                <th>Name</th>
                <th>Owner</th>
                <th>Invite</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(it=> (
                <tr key={it.id} style={{borderTop:'1px solid #ddd'}}>
                  <td style={{padding:8}}>{it.name}</td>
                  <td style={{padding:8, maxWidth:220, overflow:'hidden', textOverflow:'ellipsis'}}>{it.owner_id}</td>
                  <td style={{padding:8}}>{it.invite_code}</td>
                  <td style={{padding:8}}>{new Date((it.created_at||0)*1000).toLocaleString()}</td>
                  <td style={{padding:8}}>
                    <button onClick={()=>onDelete(it.id)} style={{background:'#d9534f', color:'white', border:'none', padding:'6px 10px', borderRadius:6}}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  )
}
