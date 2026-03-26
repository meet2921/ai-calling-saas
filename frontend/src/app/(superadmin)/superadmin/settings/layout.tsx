'use client'

import { usePathname, useRouter } from 'next/navigation'

const TABS = [
  { label: 'Profile',  href: '/superadmin/settings/profile' },
  { label: 'Security', href: '/superadmin/settings/security' },
]

export default function SuperAdminSettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Tab bar */}
      <div style={{ display: 'flex', gap: '0', borderBottom: '1px solid #e5e7eb' }}>
        {TABS.map(tab => {
          const active = pathname.startsWith(tab.href)
          return (
            <button
              key={tab.href}
              onClick={() => router.push(tab.href)}
              style={{
                padding: '10px 24px',
                fontSize: '14px',
                fontWeight: active ? '600' : '400',
                color: active ? '#2563eb' : '#6b7280',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                borderBottom: active ? '2px solid #2563eb' : '2px solid transparent',
                marginBottom: '-1px',
              }}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Page content */}
      {children}
    </div>
  )
}
