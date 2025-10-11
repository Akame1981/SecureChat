import Link from 'next/link'
import { useRouter } from 'next/router'

const links = [
  { href: '/', label: 'Overview' },
  { href: '/system', label: 'System' },
  { href: '/users', label: 'Users' },
  { href: '/messages', label: 'Messages' },
  { href: '/servers', label: 'Servers' },
  { href: '/attachments', label: 'Attachments' },
  { href: '/settings', label: 'Settings' },
]

export default function Sidebar() {
  const router = useRouter()
  return (
    <aside className="w-56 bg-gray-800 p-4 space-y-4">
      <div className="text-xl font-bold">Whispr</div>
      <nav className="space-y-2">
        {links.map(l => (
          <Link key={l.href} href={l.href} className={`block px-2 py-1 rounded hover:bg-gray-700 ${router.pathname === l.href ? 'bg-gray-700' : ''}`}>{l.label}</Link>
        ))}
      </nav>
    </aside>
  )
}
