'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi } from '@/lib/api/admin'
import { Eye, Search, SlidersHorizontal } from 'lucide-react'

interface DashboardData {
  organizations: { total: number; active: number; suspended: number }
  users: { total_admins: number }
  calls: { total_calls: number; total_minutes_used: number }
  revenue: { total_amount_paid_inr: number }
  alerts: { orgs_with_zero_balance: number }
  campaigns: { total: number }
}

function StatCard({
  title,
  value,
  sub,
  subColor = '#16a34a',
  highlight = false,
}: {
  title: string
  value: string | number
  sub?: string
  subColor?: string
  highlight?: boolean
}) {
  return (
    <div
      style={{
        backgroundColor: highlight ? '#F5A623' : 'white',
        border: highlight ? 'none' : '1px solid #e5e7eb',
        borderRadius: '12px',
        padding: '16px 20px',
        minHeight: '100px',
      }}
    >
      <p style={{
        fontSize: '13px',
        fontWeight: '500',
        color: highlight ? 'rgba(255,255,255,0.9)' : '#6b7280',
        marginBottom: '8px',
      }}>
        {title}
      </p>
      <p style={{
        fontSize: '28px',
        fontWeight: '700',
        color: highlight ? 'white' : '#111827',
        lineHeight: '1',
        marginBottom: '6px',
      }}>
        {value}
      </p>
      {sub && (
        <p style={{
          fontSize: '12px',
          fontWeight: '500',
          color: highlight ? 'rgba(255,255,255,0.85)' : subColor,
        }}>
          {sub}
        </p>
      )}
    </div>
  )
}

export default function SuperAdminDashboard() {
  const router = useRouter()
  const [data, setData] = useState<DashboardData | null>(null)
  const [orgs, setOrgs] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([adminApi.dashboard(), adminApi.orgs()])
      .then(([dashRes, orgsRes]) => {
        setData(dashRes.data)
        const list = Array.isArray(orgsRes.data)
          ? orgsRes.data
          : orgsRes.data?.organizations ?? []
        setOrgs(list.slice(0, 5))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = orgs.filter(o =>
    o.name?.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {[...Array(3)].map((_, i) => (
          <div key={i} style={{ height: '100px', backgroundColor: '#e5e7eb', borderRadius: '12px' }} />
        ))}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Platform stats */}
      <div>
        <p style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '12px' }}>
          Platform stats
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          <StatCard
            title="Total Organizations"
            value={data?.organizations.total ?? 0}
          />
          <StatCard
            title="Active Organizations"
            value={data?.organizations.active ?? 0}
          />
          <StatCard
            title="Suspended Organizations"
            value={data?.organizations.suspended ?? 0}
          />
          <StatCard
            title="Total Revenue Collected"
            value={`₹${(data?.revenue.total_amount_paid_inr ?? 0).toLocaleString('en-IN')}`}
          />
        </div>
      </div>

      {/* Activity stats */}
      <div>
        <p style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '12px' }}>
          Activity stats
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          <StatCard
            title="Total Campaigns"
            value={data?.campaigns.total ?? 0}
          />
          <StatCard
            title="Total Calls Made"
            value={(data?.calls.total_calls ?? 0).toLocaleString('en-IN')}
          />
          <StatCard
            title="Total Minutes Used"
            value={`${(data?.calls.total_minutes_used ?? 0).toLocaleString('en-IN')} min`}
          />
          <StatCard
            title="Organizations with Zero Balance"
            value={data?.alerts.orgs_with_zero_balance ?? 0}
            highlight
          />
        </div>
      </div>

      {/* Recent Organizations */}
      <div>
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <p style={{ fontSize: '15px', fontWeight: '700', color: '#111827' }}>
            Recent Organizations
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              backgroundColor: 'white', border: '1px solid #e5e7eb',
              borderRadius: '10px', padding: '8px 12px',
            }}>
              <Search size={14} style={{ color: '#9ca3af' }} />
              <input
                type="text"
                placeholder="Search"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{
                  border: 'none', outline: 'none', fontSize: '13px',
                  color: '#374151', backgroundColor: 'transparent', width: '140px',
                }}
              />
            </div>
            <button style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              backgroundColor: 'white', border: '1px solid #e5e7eb',
              borderRadius: '10px', padding: '8px 12px',
              fontSize: '13px', fontWeight: '500', color: '#4F8EF7', cursor: 'pointer',
            }}>
              <SlidersHorizontal size={14} />
              Filter
            </button>
          </div>
        </div>

        {/* Table */}
        <div style={{
          backgroundColor: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '12px',
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                {['Organization', 'Status', 'Users', 'Campaigns', 'Minutes Balance', 'View'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '12px 20px',
                    fontSize: '13px', fontWeight: '700', color: '#374151',
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '40px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>
                    No organizations found
                  </td>
                </tr>
              ) : (
                filtered.map((org, i) => (
                  <tr
                    key={org.id}
                    style={{
                      borderBottom: i < filtered.length - 1 ? '1px solid #f3f4f6' : 'none',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                  >
                    <td style={{ padding: '14px 20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{
                          width: '32px', height: '32px', borderRadius: '50%',
                          backgroundColor: '#e5e7eb', display: 'flex',
                          alignItems: 'center', justifyContent: 'center',
                          fontSize: '12px', fontWeight: '600', color: '#6b7280',
                        }}>
                          {org.name?.[0]?.toUpperCase()}
                        </div>
                        <span style={{ fontSize: '14px', fontWeight: '500', color: '#111827' }}>
                          {org.name}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '14px 20px' }}>
                      <span style={{
                        fontSize: '13px', fontWeight: '600',
                        color: org.is_active ? '#16a34a' : '#dc2626',
                      }}>
                        • {org.is_active ? 'Active' : 'Suspended'}
                      </span>
                    </td>
                    <td style={{ padding: '14px 20px', fontSize: '14px', color: '#374151' }}>
                      {org.user_count ?? '—'}
                    </td>
                    <td style={{ padding: '14px 20px', fontSize: '14px', color: '#374151' }}>
                      {org.campaign_count ?? '—'}
                    </td>
                    <td style={{ padding: '14px 20px', fontSize: '14px', color: '#374151' }}>
                      {org.minutes_balance != null ? `${org.minutes_balance} min` : '—'}
                    </td>
                    <td style={{ padding: '14px 20px' }}>
                      <button
                        onClick={() => router.push(`/superadmin/organizations/${org.id}`)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af' }}
                      >
                        <Eye size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          <div style={{
            padding: '10px 20px', borderTop: '1px solid #f3f4f6',
            display: 'flex', justifyContent: 'flex-end',
          }}>
            <button
              onClick={() => router.push('/superadmin/organizations')}
              style={{ fontSize: '13px', color: '#6b7280', background: 'none', border: 'none', cursor: 'pointer' }}
            >
              View all
            </button>
          </div>
        </div>
      </div>

    </div>
  )
}