'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi } from '@/lib/api/admin'
import { Search, SlidersHorizontal, X } from 'lucide-react'

interface Campaign {
  id: string
  name: string
  status: string
  bolna_agent_id: string | null
  created_at: string
  organization_id: string
  organization_name: string
  total_leads: number
  total_calls: number
}

const STATUS_STYLE: Record<string, { color: string; bg: string }> = {
  running:   { color: '#16a34a', bg: '#f0fdf4' },
  active:    { color: '#16a34a', bg: '#f0fdf4' },
  paused:    { color: '#d97706', bg: '#fffbeb' },
  draft:     { color: '#6b7280', bg: '#f3f4f6' },
  stopped:   { color: '#ef4444', bg: '#fef2f2' },
  completed: { color: '#2563eb', bg: '#eff6ff' },
}

const ALL_STATUSES = ['all', 'draft', 'running', 'paused', 'stopped', 'completed']

function fmtDate(iso?: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

function SkeletonRow() {
  return (
    <tr style={{ borderBottom: '1px solid #f3f4f6' }}>
      {[35, 25, 20, 15, 15, 20].map((w, i) => (
        <td key={i} style={{ padding: '16px 20px' }}>
          <div style={{ height: '12px', width: `${w}%`, backgroundColor: '#e5e7eb', borderRadius: '6px' }} />
        </td>
      ))}
    </tr>
  )
}

export default function SuperAdminCampaignsPage() {
  const router = useRouter()
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [filterOpen, setFilterOpen] = useState(false)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  useEffect(() => {
    adminApi.campaigns()
      .then(res => {
        const list = Array.isArray(res.data) ? res.data : res.data?.campaigns ?? []
        setCampaigns(list)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = campaigns.filter(c => {
    const matchSearch = `${c.name} ${c.organization_name}`.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || c.status === statusFilter
    return matchSearch && matchStatus
  })

  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage))
  const paginated = filtered.slice((page - 1) * perPage, page * perPage)
  const hasFilters = search !== '' || statusFilter !== 'all'

  const clearFilters = () => { setSearch(''); setStatusFilter('all'); setPage(1) }

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
            placeholder="Search by campaign name or organization..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            style={{ flex: 1, border: 'none', outline: 'none', fontSize: '13px', color: '#374151', backgroundColor: 'transparent' }}
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
            {statusFilter !== 'all' && (
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#2563eb', display: 'inline-block', marginLeft: '2px' }} />
            )}
          </button>

          {filterOpen && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 8px)', left: 0, zIndex: 50,
              backgroundColor: 'white', border: '1px solid #e5e7eb',
              borderRadius: '12px', padding: '14px', minWidth: '160px',
              boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
            }}>
              <p style={{ fontSize: '11px', fontWeight: '600', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>Status</p>
              {ALL_STATUSES.map(s => (
                <button key={s} onClick={() => { setStatusFilter(s); setPage(1) }}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '7px 10px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                    fontSize: '13px', fontWeight: statusFilter === s ? '600' : '400',
                    backgroundColor: statusFilter === s ? '#eff6ff' : 'transparent',
                    color: statusFilter === s ? '#2563eb' : '#374151',
                    textTransform: 'capitalize',
                  }}>
                  {s === 'all' ? 'All statuses' : s}
                </button>
              ))}
              {statusFilter !== 'all' && (
                <button onClick={() => { setStatusFilter('all'); setPage(1); setFilterOpen(false) }}
                  style={{ display: 'block', width: '100%', textAlign: 'center', marginTop: '10px', padding: '7px', borderRadius: '8px', border: '1px solid #e5e7eb', backgroundColor: 'white', fontSize: '12px', fontWeight: '600', color: '#6b7280', cursor: 'pointer' }}>
                  Clear
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Table / states */}
      {loading ? (
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                {['Campaign', 'Organization', 'Status', 'Leads', 'Calls', 'Created'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '13px', fontWeight: '700', color: '#374151' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>{[...Array(6)].map((_, i) => <SkeletonRow key={i} />)}</tbody>
          </table>
        </div>

      ) : campaigns.length === 0 ? (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '16px', padding: '80px 24px',
        }}>
          <div style={{ fontSize: '72px', marginBottom: '16px', lineHeight: 1 }}>🚀</div>
          <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>No campaigns yet</p>
          <p style={{ fontSize: '14px', color: '#6b7280', textAlign: 'center', maxWidth: '320px' }}>
            Campaigns will appear here once organizations start creating them.
          </p>
        </div>

      ) : paginated.length === 0 && hasFilters ? (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '16px', padding: '80px 24px',
        }}>
          <div style={{ fontSize: '72px', marginBottom: '16px', lineHeight: 1 }}>🔍</div>
          <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>No campaigns found</p>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '24px' }}>Try adjusting your search or filter criteria.</p>
          <button onClick={clearFilters}
            style={{ backgroundColor: 'white', color: '#2563eb', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 24px', fontSize: '14px', fontWeight: '600', cursor: 'pointer' }}>
            Clear Filters
          </button>
        </div>

      ) : (
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                {['Campaign', 'Organization', 'Status', 'Leads', 'Calls', 'Created'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '13px', fontWeight: '700', color: '#374151', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginated.map((c, i) => {
                const st = STATUS_STYLE[c.status?.toLowerCase()] ?? STATUS_STYLE.draft
                return (
                  <tr
                    key={c.id}
                    style={{ borderBottom: i < paginated.length - 1 ? '1px solid #f3f4f6' : 'none', cursor: 'pointer' }}
                    onClick={() => router.push(`/superadmin/organizations/${c.organization_id}`)}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                  >
                    {/* Campaign name */}
                    <td style={{ padding: '14px 20px' }}>
                      <p style={{ fontSize: '13px', fontWeight: '600', color: '#111827', margin: 0 }}>{c.name}</p>
                      {c.bolna_agent_id && (
                        <p style={{ fontSize: '11px', color: '#9ca3af', margin: '2px 0 0', fontFamily: 'monospace' }}>
                          {c.bolna_agent_id.slice(0, 16)}…
                        </p>
                      )}
                    </td>

                    {/* Organization */}
                    <td style={{ padding: '14px 20px', fontSize: '13px', fontWeight: '500', color: '#374151' }}>
                      {c.organization_name}
                    </td>

                    {/* Status */}
                    <td style={{ padding: '14px 20px' }}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: '5px',
                        fontSize: '12px', fontWeight: '600', textTransform: 'capitalize',
                        color: st.color, backgroundColor: st.bg,
                        padding: '3px 10px', borderRadius: '20px',
                      }}>
                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: st.color, display: 'inline-block' }} />
                        {c.status}
                      </span>
                    </td>

                    {/* Leads */}
                    <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>
                      {(c.total_leads ?? 0).toLocaleString('en-IN')}
                    </td>

                    {/* Calls */}
                    <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>
                      {(c.total_calls ?? 0).toLocaleString('en-IN')}
                    </td>

                    {/* Created */}
                    <td style={{ padding: '14px 20px', fontSize: '13px', color: '#6b7280', whiteSpace: 'nowrap' }}>
                      {fmtDate(c.created_at)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {/* Pagination */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', borderTop: '1px solid #f3f4f6', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <select value={perPage} onChange={e => { setPerPage(Number(e.target.value)); setPage(1) }}
                style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '4px 8px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer', outline: 'none' }}>
                {[10, 20, 50].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
              <span style={{ fontSize: '13px', color: '#6b7280' }}>Items per page</span>
              <span style={{ fontSize: '13px', color: '#6b7280', marginLeft: '8px' }}>
                {Math.min((page - 1) * perPage + 1, filtered.length)}–{Math.min(page * perPage, filtered.length)} of {filtered.length} items
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <select value={page} onChange={e => setPage(Number(e.target.value))}
                style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '4px 8px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer', outline: 'none' }}>
                {[...Array(totalPages)].map((_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
              </select>
              <span style={{ fontSize: '13px', color: '#6b7280' }}>of {totalPages} pages</span>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                style={{ width: '28px', height: '28px', borderRadius: '8px', border: '1px solid #e5e7eb', backgroundColor: 'white', cursor: page === 1 ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: page === 1 ? '#d1d5db' : '#6b7280', fontSize: '14px' }}>
                ‹
              </button>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                style={{ width: '28px', height: '28px', borderRadius: '8px', border: '1px solid #e5e7eb', backgroundColor: 'white', cursor: page === totalPages ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: page === totalPages ? '#d1d5db' : '#6b7280', fontSize: '14px' }}>
                ›
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
