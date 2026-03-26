'use client'

import { useState, useEffect } from 'react'
import AdminSidebar from '@/components/layout/AdminSidebar'
import TopHeader from '@/components/layout/TopHeader'
import { useAuthStore } from '@/store/auth.store'
import { authApi } from '@/lib/api/auth'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user, setUser } = useAuthStore()

  useEffect(() => {
    if (!user) {
      authApi.me().then(res => setUser(res.data)).catch(() => {})
    }
  }, [])

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: '#f9fafb' }}>
      <AdminSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopHeader onMenuClick={() => setSidebarOpen(prev => !prev)} />
        <main className="flex-1 overflow-y-auto" style={{ padding: '16px 24px 24px' }}>
          {children}
        </main>
      </div>
    </div>
  )
}