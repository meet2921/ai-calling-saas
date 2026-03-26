'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi } from '@/lib/api/admin'
import { Search, SlidersHorizontal, Plus, Eye, X } from 'lucide-react'

interface Org {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at?: string
  // flat (legacy fallback)
  user_count?: number
  campaign_count?: number
  minutes_balance?: number
  total_amount_paid?: number
  // nested (actual API shape)
  stats?: { total_users?: number; total_campaigns?: number }
  wallet?: { minutes_balance?: number; total_amount_paid?: number }
}

function SkeletonRow() {
  return (
    <tr style={{ borderBottom: '1px solid #f3f4f6' }}>
      {[40, 80, 40, 50, 70, 70, 70, 80].map((w, i) => (
        <td key={i} style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {i === 0 && (
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#e5e7eb', flexShrink: 0 }} />
            )}
            <div style={{ height: '12px', width: `${w}%`, backgroundColor: '#e5e7eb', borderRadius: '6px' }} />
          </div>
        </td>
      ))}
    </tr>
  )
}

export default function OrganizationsPage() {
  const router = useRouter()
  const [orgs, setOrgs] = useState<Org[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterOpen, setFilterOpen] = useState(false)
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'suspended'>('all')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  useEffect(() => {
    adminApi.orgs()
      .then(res => {
        const list = Array.isArray(res.data)
          ? res.data
          : res.data?.organizations ?? []
        setOrgs(list)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = orgs.filter(o => {
    const matchSearch =
      o.name?.toLowerCase().includes(search.toLowerCase()) ||
      o.slug?.toLowerCase().includes(search.toLowerCase())
    const matchStatus =
      statusFilter === 'all' ||
      (statusFilter === 'active' && o.is_active) ||
      (statusFilter === 'suspended' && !o.is_active)
    return matchSearch && matchStatus
  })

  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage))
  const paginated = filtered.slice((page - 1) * perPage, page * perPage)
  const hasFilters = search !== '' || statusFilter !== 'all'

  const clearFilters = () => {
    setSearch('')
    setStatusFilter('all')
    setPage(1)
  }

  const formatDate = (iso?: string) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        {/* Search */}
        <div style={{
          flex: 1, minWidth: '260px', display: 'flex', alignItems: 'center', gap: '8px',
          backgroundColor: 'white', border: '1px solid #e5e7eb',
          borderRadius: '10px', padding: '10px 14px',
        }}>
          <Search size={15} style={{ color: '#9ca3af', flexShrink: 0 }} />
          <input
            type="text"
            placeholder="Search by organization name or slug..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            style={{
              flex: 1, border: 'none', outline: 'none',
              fontSize: '13px', color: '#374151', backgroundColor: 'transparent',
            }}
          />
          {search && (
            <button onClick={() => { setSearch(''); setPage(1) }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', padding: 0, display: 'flex' }}>
              <X size={14} />
            </button>
          )}
        </div>

        {/* Filter */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setFilterOpen(v => !v)}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              backgroundColor: filterOpen ? '#eff6ff' : 'white',
              border: `1px solid ${filterOpen ? '#93c5fd' : '#e5e7eb'}`,
              borderRadius: '10px', padding: '10px 14px',
              fontSize: '13px', fontWeight: '500',
              color: filterOpen ? '#2563eb' : '#374151', cursor: 'pointer',
            }}
          >
            <SlidersHorizontal size={14} />
            Filter
          </button>

          {filterOpen && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 8px)', left: 0, zIndex: 50,
              backgroundColor: 'white', border: '1px solid #e5e7eb',
              borderRadius: '12px', padding: '12px', minWidth: '160px',
              boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
            }}>
              <p style={{ fontSize: '11px', fontWeight: '600', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Status</p>
              {(['all', 'active', 'suspended'] as const).map(s => (
                <button
                  key={s}
                  onClick={() => { setStatusFilter(s); setPage(1); setFilterOpen(false) }}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '8px 10px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                    fontSize: '13px', fontWeight: statusFilter === s ? '600' : '400',
                    backgroundColor: statusFilter === s ? '#eff6ff' : 'transparent',
                    color: statusFilter === s ? '#2563eb' : '#374151',
                  }}
                >
                  {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Add Organization */}
        <button
          onClick={() => router.push('/superadmin/organizations/new')}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            backgroundColor: '#2563eb', color: 'white',
            border: 'none', borderRadius: '10px', padding: '10px 18px',
            fontSize: '13px', fontWeight: '600', cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          <Plus size={15} />
          Add Organization
        </button>
      </div>

      {/* Content */}
      {loading ? (
        /* Loading skeleton */
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                {['Organization', 'Status', 'Users', 'Campaigns', 'Minutes Balance', 'Total Amount Paid', 'Created Date', 'Actions'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '13px', fontWeight: '700', color: '#374151' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...Array(4)].map((_, i) => <SkeletonRow key={i} />)}
            </tbody>
          </table>
        </div>
      ) : orgs.length === 0 ? (
        /* Empty state — no orgs at all */
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          backgroundColor: 'white', border: '1px solid #e5e7eb',
          borderRadius: '16px', padding: '80px 24px',
        }}>
          <div style={{ fontSize: '80px', marginBottom: '16px', lineHeight: 1 }}>🏢</div>
          <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>No organizations yet</p>
          <p style={{ fontSize: '14px', color: '#6b7280', textAlign: 'center', marginBottom: '24px', maxWidth: '320px' }}>
            Organizations you create will appear here.<br />Register your first organization to get started.
          </p>
          <button
            onClick={() => router.push('/superadmin/organizations/new')}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              backgroundColor: '#2563eb', color: 'white',
              border: 'none', borderRadius: '10px', padding: '11px 20px',
              fontSize: '14px', fontWeight: '600', cursor: 'pointer',
            }}
          >
            <Plus size={16} />
            Add Organization
          </button>
        </div>
      ) : paginated.length === 0 && hasFilters ? (
        /* No results after filter/search */
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          backgroundColor: 'white', border: '1px solid #e5e7eb',
          borderRadius: '16px', padding: '80px 24px',
        }}>
          <div style={{ fontSize: '72px', marginBottom: '16px', lineHeight: 1 }}>🔍</div>
          <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>No organizations found</p>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '24px' }}>Try adjusting your search or filter criteria.</p>
          <button
            onClick={clearFilters}
            style={{
              backgroundColor: 'white', color: '#2563eb',
              border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 24px',
              fontSize: '14px', fontWeight: '600', cursor: 'pointer',
            }}
          >
            Clear Filters
          </button>
        </div>
      ) : (
        /* Data table */
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                {['Organization', 'Status', 'Users', 'Campaigns', 'Minutes Balance', 'Total Amount Paid', 'Created Date', 'Actions'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '13px', fontWeight: '700', color: '#374151', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginated.map((org, i) => {
                const totalUsers    = org.stats?.total_users    ?? org.user_count
                const totalCampaigns = org.stats?.total_campaigns ?? org.campaign_count
                const minutesBalance = org.wallet?.minutes_balance ?? org.minutes_balance
                const totalAmountPaid = org.wallet?.total_amount_paid ?? org.total_amount_paid
                const lowBalance = (minutesBalance ?? 0) < 200
                return (
                  <tr
                    key={org.id}
                    style={{ borderBottom: i < paginated.length - 1 ? '1px solid #f3f4f6' : 'none' }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                  >
                    {/* Organization */}
                    <td style={{ padding: '14px 20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{
                          width: '32px', height: '32px', borderRadius: '50%',
                          backgroundColor: '#e5e7eb', display: 'flex', alignItems: 'center',
                          justifyContent: 'center', fontSize: '12px', fontWeight: '600',
                          color: '#6b7280', flexShrink: 0,
                        }}>
                          {org.name?.[0]?.toUpperCase()}
                        </div>
                        <div>
                          <p style={{ fontSize: '13px', fontWeight: '600', color: '#111827', lineHeight: '1.2' }}>{org.name}</p>
                          <p style={{ fontSize: '11px', color: '#9ca3af', lineHeight: '1.2' }}>{org.slug}</p>
                        </div>
                      </div>
                    </td>

                    {/* Status */}
                    <td style={{ padding: '14px 20px' }}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: '5px',
                        fontSize: '12px', fontWeight: '600',
                        color: org.is_active ? '#16a34a' : '#dc2626',
                        backgroundColor: org.is_active ? '#f0fdf4' : '#fef2f2',
                        padding: '3px 10px', borderRadius: '20px',
                      }}>
                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor', display: 'inline-block' }} />
                        {org.is_active ? 'Active' : 'Suspended'}
                      </span>
                    </td>

                    {/* Users */}
                    <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>
                      {totalUsers ?? '—'}
                    </td>

                    {/* Campaigns */}
                    <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>
                      {totalCampaigns ?? '—'}
                    </td>

                    {/* Minutes Balance */}
                    <td style={{ padding: '14px 20px', fontSize: '13px', color: lowBalance ? '#dc2626' : '#374151', fontWeight: lowBalance ? '600' : '400' }}>
                      {minutesBalance != null ? `${minutesBalance} min` : '—'}
                    </td>

                    {/* Total Amount Paid */}
                    <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>
                      {totalAmountPaid != null ? `₹${totalAmountPaid.toLocaleString('en-IN')}` : '—'}
                    </td>

                    {/* Created Date */}
                    <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151', whiteSpace: 'nowrap' }}>
                      {formatDate(org.created_at)}
                    </td>

                    {/* Actions */}
                    <td style={{ padding: '14px 20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                          onClick={() => router.push(`/superadmin/organizations/${org.id}`)}
                          title="View"
                          style={{
                            width: '30px', height: '30px', borderRadius: '8px',
                            border: '1px solid #e5e7eb', backgroundColor: 'white',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            cursor: 'pointer', color: '#6b7280',
                          }}
                          onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f3f4f6'}
                          onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'white'}
                        >
                          <Eye size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {/* Pagination */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 20px', borderTop: '1px solid #f3f4f6',
            flexWrap: 'wrap', gap: '8px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <select
                value={perPage}
                onChange={e => { setPerPage(Number(e.target.value)); setPage(1) }}
                style={{
                  border: '1px solid #e5e7eb', borderRadius: '8px',
                  padding: '4px 8px', fontSize: '13px', color: '#374151',
                  backgroundColor: 'white', cursor: 'pointer', outline: 'none',
                }}
              >
                {[10, 20, 50].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
              <span style={{ fontSize: '13px', color: '#6b7280' }}>Items per page</span>
              <span style={{ fontSize: '13px', color: '#6b7280', marginLeft: '8px' }}>
                {Math.min((page - 1) * perPage + 1, filtered.length)}–{Math.min(page * perPage, filtered.length)} of {filtered.length} items
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <select
                value={page}
                onChange={e => setPage(Number(e.target.value))}
                style={{
                  border: '1px solid #e5e7eb', borderRadius: '8px',
                  padding: '4px 8px', fontSize: '13px', color: '#374151',
                  backgroundColor: 'white', cursor: 'pointer', outline: 'none',
                }}
              >
                {[...Array(totalPages)].map((_, i) => (
                  <option key={i + 1} value={i + 1}>{i + 1}</option>
                ))}
              </select>
              <span style={{ fontSize: '13px', color: '#6b7280' }}>of {totalPages} pages</span>
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{
                  width: '28px', height: '28px', borderRadius: '8px', border: '1px solid #e5e7eb',
                  backgroundColor: 'white', cursor: page === 1 ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: page === 1 ? '#d1d5db' : '#6b7280', fontSize: '14px',
                }}
              >
                ‹
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                style={{
                  width: '28px', height: '28px', borderRadius: '8px', border: '1px solid #e5e7eb',
                  backgroundColor: 'white', cursor: page === totalPages ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: page === totalPages ? '#d1d5db' : '#6b7280', fontSize: '14px',
                }}
              >
                ›
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
