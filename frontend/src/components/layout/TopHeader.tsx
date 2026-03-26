'use client'

import { Menu, Moon, Sun, User, LogOut } from 'lucide-react'
import { useAuthStore } from '@/store/auth.store'
import { usePathname, useRouter } from 'next/navigation'
import { useState, useRef, useEffect } from 'react'

function getPageTitle(pathname: string): string {
  if (pathname === '/superadmin')                                return 'Dashboard'
  if (pathname === '/superadmin/organizations/new')             return 'Register new form'
  if (/^\/superadmin\/organizations\/[^/]+$/.test(pathname))   return 'Organization detail'
  if (pathname.startsWith('/superadmin/organizations'))         return 'Organisation'
  if (pathname.startsWith('/superadmin/users'))         return 'Users'
  if (pathname.startsWith('/superadmin/campaigns'))     return 'Campaigns'
  if (pathname.startsWith('/superadmin/settings/profile'))  return 'Profile'
  if (pathname.startsWith('/superadmin/settings/security')) return 'Security'
  if (pathname.startsWith('/superadmin/settings'))          return 'Settings'
  if (pathname === '/dashboard')                        return 'Dashboard'
  if (/^\/campaigns\/[^/]+\/analytics$/.test(pathname)) return 'Analytics'
  if (/^\/campaigns\/[^/]+\/call-logs$/.test(pathname)) return 'Call logs'
  if (/^\/campaigns\/[^/]+\/leads$/.test(pathname))     return 'Leads'
  if (pathname.startsWith('/campaigns'))                return 'Campaigns'
  if (pathname.startsWith('/wallet'))                   return 'Wallet'
  if (pathname.startsWith('/settings/profile'))          return 'Profile'
  if (pathname.startsWith('/settings/security'))         return 'Security'
  if (pathname.startsWith('/settings'))                 return 'Settings'
  return 'Dashboard'
}

interface Props {
  onMenuClick: () => void
}

export default function TopHeader({ onMenuClick }: Props) {
  const { user, clearAuth } = useAuthStore()
  const pathname = usePathname()
  const router = useRouter()
  const title = getPageTitle(pathname)
  const [darkMode, setDarkMode] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = () => {
    clearAuth()
    router.push('/login')
  }

  return (
    <div style={{ padding: '12px 24px 0', backgroundColor: '#f9fafb' }}>
      <header
        style={{
          backgroundColor: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '16px',
          padding: '0 20px',
          height: '60px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Left — hamburger + title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={onMenuClick}
            style={{
              padding: '6px',
              borderRadius: '8px',
              color: '#6b7280',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Menu size={20} />
          </button>
          <h1 style={{ fontSize: '18px', fontWeight: '700', color: '#111827', margin: 0 }}>
            {title}
          </h1>
        </div>

        {/* Right — dark mode toggle + avatar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>

          {/* Dark/Light toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Moon size={16} style={{ color: '#9ca3af' }} />
            <button
              onClick={() => setDarkMode(!darkMode)}
              style={{
                width: '44px',
                height: '24px',
                borderRadius: '12px',
                backgroundColor: darkMode ? '#3b82f6' : '#3b82f6',
                border: 'none',
                cursor: 'pointer',
                position: 'relative',
                transition: 'background-color 0.2s',
              }}
            >
              <div
                style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  backgroundColor: 'white',
                  position: 'absolute',
                  top: '3px',
                  left: darkMode ? '23px' : '3px',
                  transition: 'left 0.2s',
                }}
              />
            </button>
            <Sun size={16} style={{ color: '#9ca3af' }} />
          </div>

          {/* User avatar + dropdown */}
          <div ref={dropdownRef} style={{ position: 'relative' }}>
            <div
              onClick={() => setDropdownOpen(o => !o)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
            >
              <div
                style={{
                  width: '36px', height: '36px', borderRadius: '50%',
                  backgroundColor: '#6b7280',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '14px', fontWeight: '600', color: 'white',
                }}
              >
                {user?.first_name?.[0]?.toUpperCase() ?? 'U'}
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </div>

            {dropdownOpen && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 10px)', right: 0,
                backgroundColor: 'white', border: '1px solid #e5e7eb',
                borderRadius: '12px', boxShadow: '0 8px 24px rgba(0,0,0,0.10)',
                minWidth: '180px', zIndex: 100, overflow: 'hidden',
              }}>
                {/* User info */}
                <div style={{ padding: '12px 16px', borderBottom: '1px solid #f3f4f6' }}>
                  <p style={{ fontSize: '13px', fontWeight: '600', color: '#111827', margin: '0 0 2px' }}>
                    {user?.first_name} {user?.last_name}
                  </p>
                  <p style={{ fontSize: '12px', color: '#9ca3af', margin: 0 }}>{user?.email}</p>
                </div>
                {/* Profile */}
                <button
                  onClick={() => {
                    setDropdownOpen(false)
                    const isSuperAdmin = user?.role === 'super_admin'
                    router.push(isSuperAdmin ? '/superadmin/settings/profile' : '/settings/profile')
                  }}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '11px 16px', background: 'none', border: 'none',
                    fontSize: '13px', fontWeight: '500', color: '#374151',
                    cursor: 'pointer', textAlign: 'left',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#f9fafb')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <User size={15} style={{ color: '#6b7280' }} /> Profile
                </button>
                {/* Logout */}
                <button
                  onClick={handleLogout}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '11px 16px', background: 'none', border: 'none',
                    borderTop: '1px solid #f3f4f6',
                    fontSize: '13px', fontWeight: '500', color: '#ef4444',
                    cursor: 'pointer', textAlign: 'left',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#fff1f2')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <LogOut size={15} /> Logout
                </button>
              </div>
            )}
          </div>

        </div>
      </header>
    </div>
  )
}