'use client'

import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Building2, Users,
  Settings, Rocket
} from 'lucide-react'
import { cn } from '@/lib/utils/cn'
import { useAuthStore } from '@/store/auth.store'

const navItems = [
  { label: 'Dashboard',    href: '/superadmin',               icon: LayoutDashboard },
  { label: 'Organisation', href: '/superadmin/organizations', icon: Building2 },
  { label: 'Users',        href: '/superadmin/users',         icon: Users },
  { label: 'Campaigns',    href: '/superadmin/campaigns',     icon: Rocket },
]

const bottomItems = [
  { label: 'Settings', href: '/superadmin/settings', icon: Settings },
]

interface Props {
  open: boolean
  onClose: () => void
}

export default function SuperAdminSidebar({ open, onClose }: Props) {
  const pathname = usePathname()
  const { user } = useAuthStore()

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-20 lg:hidden"
          style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'flex flex-col h-full z-30',
          'transition-all duration-300 ease-in-out',
          // Mobile: fixed overlay
          'fixed lg:static top-0 left-0',
          // Mobile hide/show
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
        style={{
          width: open ? '240px' : '72px',
          backgroundColor: 'white',
          borderRight: '1px solid #e5e7eb',
          overflow: 'hidden',
          padding: '15px 0',
        }}
      >
        {/* Logo */}
        <div
          className="flex items-center shrink-0"
          style={{
            height: '80px',
            borderBottom: '1px solid #e5e7eb',
            padding: open ? '0 20px' : '0',
            justifyContent: open ? 'flex-start' : 'center',
          }}
        >
          <img
            src={open ? '/logo2.png' : '/logo.png'}
            alt="Logo"
            style={{
              height: open ? '180px' : '40px',
              borderRadius: '4px',
              width: 'auto',
              objectFit: 'contain',
            }}
          />
        </div>

        {/* Nav items */}
        <nav
          className="flex-1 overflow-y-auto overflow-x-hidden"
          style={{
            paddingTop: '16px',
            paddingBottom: '16px',
            paddingLeft: open ? '16px' : '10px',
            paddingRight: open ? '16px' : '10px',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' , width: '100%'}}>
            {navItems.map(({ label, href, icon: Icon }) => {
              const active = pathname === href || (href !== '/superadmin' && pathname.startsWith(href))
              return (
                <a
                  key={href}
                  href={href}
                  onClick={() => { if (window.innerWidth < 1024) onClose() }}
                  title={!open ? label : undefined}
                  className="flex items-center transition-all duration-150 w-full"
                  style={{
                    gap: open ? '12px' : '0',
                    padding: open ? '12px 16px' : '12px 0',
                    justifyContent: open ? 'flex-start' : 'center',
                    borderRadius: '16px',
                    backgroundColor: active ? '#dbeafe' : 'transparent',
                    color: active ? '#2563eb' : '#576279',
                    fontWeight: active ? '600' : '400',
                    fontSize: '14px',
                  }}
                  onMouseEnter={e => {
                    if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = '#f3f4f6'
                  }}
                  onMouseLeave={e => {
                    if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'
                  }}
                >
                  <Icon className="w-5 h-5 shrink-0" />
                  {open && (
                    <span style={{ whiteSpace: 'nowrap' }}>{label}</span>
                  )}
                </a>
              )
            })}
          </div>
        </nav>

        {/* Bottom */}
        <div
          className="shrink-0 space-y-1"
          style={{
            borderTop: '1px solid #e5e7eb',
            paddingTop: '16px',
            paddingBottom: '16px',
            paddingLeft: open ? '12px' : '8px',
            paddingRight: open ? '12px' : '8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          {bottomItems.map(({ label, href, icon: Icon }) => (
            <a
              key={href}
              href={href}
              title={!open ? label : undefined}
              className="flex items-center transition-all duration-150 w-full"
              style={{
                gap: open ? '12px' : '0',
                padding: open ? '12px 16px' : '12px 0',
                justifyContent: open ? 'flex-start' : 'center',
                borderRadius: '16px',
                backgroundColor: 'transparent',
                color: '#576279',
                fontSize: '14px',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.backgroundColor = '#f3f4f6'
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'
              }}
            >
              <Icon className="w-5 h-5 shrink-0" />
              {open && <span style={{ whiteSpace: 'nowrap' }}>{label}</span>}
            </a>
          ))}

          {/* User */}
          {open ? (
            <div className="flex items-center gap-3 px-3 py-2 mt-1">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white shrink-0"
                style={{ backgroundColor: '#6b7280' }}
              >
                {user?.first_name?.[0]?.toUpperCase() ?? 'U'}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-800 truncate">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-gray-400 truncate">{user?.email}</p>
              </div>
            </div>
          ) : (
            <div className="flex justify-center py-2">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white"
                style={{ backgroundColor: '#6b7280' }}
              >
                {user?.first_name?.[0]?.toUpperCase() ?? 'U'}
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}