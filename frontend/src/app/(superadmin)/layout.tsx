'use client'

import { useState, useEffect } from 'react'
import SuperAdminSidebar from '@/components/layout/SuperAdminSidebar'
import TopHeader from '@/components/layout/TopHeader'
import { useAuthStore } from '@/store/auth.store'
import { authApi } from '@/lib/api/auth'

export default function SuperAdminLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, setUser } = useAuthStore()

  useEffect(() => {
    if (!user) {
      authApi.me().then(res => setUser(res.data)).catch(() => {})
    }
  }, [])

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: '#f9fafb' }}>

      {/* Sidebar — static on desktop, fixed on mobile */}
      <div
        className="shrink-0 hidden lg:block transition-all duration-300"
        style={{ width: sidebarOpen ? '240px' : '72px', }}
      >
        <SuperAdminSidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
      </div>

      {/* Mobile sidebar */}
      <div className="lg:hidden">
        <SuperAdminSidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopHeader
          onMenuClick={() => setSidebarOpen(!sidebarOpen)}
        />
      <main className="flex-1 overflow-y-auto" style={{ padding: '16px 24px 24px' }}>
                  {children}
        </main>
      </div>

    </div>
  )
}