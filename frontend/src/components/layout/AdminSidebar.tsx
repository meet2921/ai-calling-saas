'use client'

import { usePathname } from 'next/navigation'
import { LayoutDashboard, Megaphone, Wallet, Settings } from 'lucide-react'
import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils/cn'
import { useAuthStore } from '@/store/auth.store'
import { walletApi } from '@/lib/api/wallet'

const navItems = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Campaigns', href: '/campaigns', icon: Megaphone },
  { label: 'Wallet',    href: '/wallet',    icon: Wallet },
]

interface Props {
  open: boolean
  onClose: () => void
}

export default function AdminSidebar({ open, onClose }: Props) {
  const pathname = usePathname()
  const { user } = useAuthStore()
  const [balance, setBalance]           = useState<number | null>(null)
  const [totalPurchased, setTotalPurchased] = useState<number>(0)

  useEffect(() => {
    walletApi.summary()
      .then(res => {
        const d = res.data ?? {}
        setBalance(d.minutes_balance ?? 0)
        setTotalPurchased(d.total_minutes_purchased ?? 0)
      })
      .catch(() => {})
  }, [])

  const pctRemaining = totalPurchased > 0 && balance !== null
    ? Math.round((balance / totalPurchased) * 100)
    : null
  const isLow = pctRemaining !== null && pctRemaining <= 30

  const navLinkStyle = (active: boolean): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: open ? '12px' : '0',
    justifyContent: open ? 'flex-start' : 'center',
    padding: open ? '12px 16px' : '12px 0',
    borderRadius: '16px',
    backgroundColor: active ? '#dbeafe' : 'transparent',
    color: active ? '#2563eb' : '#576279',
    fontWeight: active ? '600' : '400',
    fontSize: '14px',
    textDecoration: 'none',
    cursor: 'pointer',
    border: 'none',
    width: '100%',
    transition: 'background-color 0.15s ease',
  })

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-20 lg:hidden"
          style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'flex flex-col h-screen z-30',
          'transition-all duration-300 ease-in-out',
          'fixed lg:static top-0 left-0',
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
        style={{
          width: open ? '260px' : '72px',
          backgroundColor: 'white',
          borderRight: '1px solid #e5e7eb',
          overflow: 'hidden',
        }}
      >

        {/* ── Logo ── */}
        <div
          style={{
            height: '80px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: open ? 'flex-start' : 'center',
            padding: open ? '0 20px' : '0',
            borderBottom: '1px solid #e5e7eb',
            flexShrink: 0,
          }}
        >
          <img
            src={open ? '/logo2.png' : '/logo.png'}
            alt="Logo"
            style={{ height: open ? '180px' : '40px',
               width: 'auto',
                objectFit: 'contain', 
                borderRadius: '4px' }}
          />
        </div>

        {/* ── Nav ── */}
        <nav
          style={{
            flex: 1,
            overflowY: 'auto',
            overflowX: 'hidden',
            paddingTop: '16px',
            paddingBottom: '16px',
            paddingLeft: open ? '16px' : '10px',
            paddingRight: open ? '16px' : '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          {navItems.map(({ label, href, icon: Icon }) => {
            const active = pathname === href || (href !== '/dashboard' && pathname.startsWith(href))
            return (
              <a
                key={href}
                href={href}
                onClick={() => { if (window.innerWidth < 1024) onClose() }}
                title={!open ? label : undefined}
                style={navLinkStyle(active)}
                onMouseEnter={e => {
                  if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = '#f3f4f6'
                }}
                onMouseLeave={e => {
                  if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'
                }}
              >
                <Icon size={18} style={{ flexShrink: 0 }} />
                {open && <span style={{ whiteSpace: 'nowrap' }}>{label}</span>}
              </a>
            )
          })}
        </nav>

        {/* ── Bottom ── */}
        <div
          style={{
            flexShrink: 0,
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

          {/* Wallet balance card — expanded only */}
          {open && balance !== null && (
            <div
              style={{
                padding: '14px 16px',
                borderRadius: '14px',
                backgroundColor: isLow ? '#fff1f2' : '#f8fafc',
                border: `1px solid ${isLow ? '#fecdd3' : '#e5e7eb'}`,
                marginBottom: '0',
              }}
            >
              <p style={{ fontSize: '11px', fontWeight: '500', color: '#9ca3af', marginBottom: '4px', letterSpacing: '0.01em' }}>
                Wallet balance
              </p>
              <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827', marginBottom: '10px', lineHeight: 1 }}>
                {balance.toLocaleString('en-IN')} min
              </p>
              <div style={{ height: '4px', borderRadius: '99px', backgroundColor: '#e5e7eb', overflow: 'hidden', marginBottom: '6px' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${pctRemaining ?? 0}%`,
                    borderRadius: '99px',
                    backgroundColor: isLow ? '#ef4444' : '#2563eb',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>
              <p style={{ fontSize: '11px', fontWeight: '500', color: isLow ? '#ef4444' : '#9ca3af' }}>
                {pctRemaining !== null ? `${pctRemaining}% remaining` : '—'}
              </p>
            </div>
          )}

          {/* Dot indicator — collapsed only */}
          {!open && balance !== null && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0', marginBottom: '4px' }}>
              <div style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: isLow ? '#ef4444' : '#2563eb' }} />
            </div>
          )}

          {/* Settings */}
          <a
            href="/settings/profile"
            title={!open ? 'Settings' : undefined}
            style={navLinkStyle(false)}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.backgroundColor = '#f3f4f6' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent' }}
          >
            <Settings size={18} style={{ flexShrink: 0 }} />
            {open && <span style={{ whiteSpace: 'nowrap' }}>Settings</span>}
          </a>

          {/* User info */}
          {open ? (
            <div className="flex items-center gap-3 px-3 py-2 mt-1">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white shrink-0"
                style={{ backgroundColor: '#6b7280' }}
              >
                {user?.first_name?.[0]?.toUpperCase() ?? 'U'}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-800 truncate" style={{ margin: 0 }}>
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-gray-400 truncate" style={{ margin: 0 }}>{user?.email}</p>
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
