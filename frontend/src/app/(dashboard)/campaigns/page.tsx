'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { campaignsApi } from '@/lib/api/campaigns'
import { Search, Plus, Play, Pause, Square, Trash2, BarChart2, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'

interface Campaign {
  id: string
  name: string
  status: string
  bolna_agent_id: string | null
  created_at: string
}

const STATUS_STYLE: Record<string, { color: string; dot: string; label: string }> = {
  running:   { color: '#16a34a', dot: '#16a34a', label: 'Running' },
  active:    { color: '#16a34a', dot: '#16a34a', label: 'Running' },
  draft:     { color: '#6b7280', dot: '#9ca3af', label: 'Draft' },
  paused:    { color: '#d97706', dot: '#d97706', label: 'Paused' },
  stopped:   { color: '#ef4444', dot: '#ef4444', label: 'Stopped' },
  completed: { color: '#2563eb', dot: '#2563eb', label: 'Completed' },
}

const STATUS_FILTERS = ['All', 'Draft', 'Running', 'Paused', 'Stopped', 'Completed']

export default function CampaignsPage() {
  const router = useRouter()
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('All')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const fetchCampaigns = async () => {
    try {
      const res = await campaignsApi.list()
      const list = Array.isArray(res.data)
        ? res.data
        : res.data?.campaigns ?? res.data?.results ?? []
      setCampaigns(list)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { fetchCampaigns() }, [])

  const handleAction = async (action: string, id: string) => {
    try {
      if (action === 'start') await campaignsApi.start(id)
      else if (action === 'pause') await campaignsApi.pause(id)
      else if (action === 'resume') await campaignsApi.resume(id)
      else if (action === 'stop') await campaignsApi.stop(id)
      else if (action === 'delete') {
        await campaignsApi.delete(id)
        setCampaigns(prev => prev.filter(c => c.id !== id))
        toast.success('Campaign deleted')
        return
      } else if (action === 'view') {
        router.push(`/campaigns/${id}`)
        return
      }
      await fetchCampaigns()
      toast.success('Campaign updated')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'string'
        ? detail
        : typeof detail === 'object' && detail?.message
          ? detail.message
          : 'Action failed'
      toast.error(msg)
    }
  }

  const filtered = campaigns.filter(c => {
    const matchSearch = c.name.toLowerCase().includes(search.toLowerCase())
    const matchFilter =
      activeFilter === 'All' ||
      c.status.toLowerCase() === activeFilter.toLowerCase() ||
      (activeFilter === 'Running' && c.status === 'active')
    return matchSearch && matchFilter
  })

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize)

  const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })

  const ActionBtn = ({
    label, icon, action, id, color = '#2563eb',
  }: { label: string; icon: React.ReactNode; action: string; id: string; color?: string }) => (
    <button
      onClick={() => handleAction(action, id)}
      style={{
        display: 'flex', alignItems: 'center', gap: '5px',
        padding: '5px 12px', borderRadius: '8px', fontSize: '13px', fontWeight: '500',
        border: `1px solid ${color}`, color, backgroundColor: 'white', cursor: 'pointer',
      }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f0f7ff'}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'white'}
    >
      {icon} {label}
    </button>
  )

  const renderActions = (c: Campaign) => {
    const s = c.status
    if (s === 'running' || s === 'active') return (
      <div style={{ display: 'flex', gap: '8px' }}>
        <ActionBtn label="Pause"  icon={<Pause size={13} />}    action="pause"  id={c.id} />
        <ActionBtn label="Stop"   icon={<Square size={13} />}   action="stop"   id={c.id} />
      </div>
    )
    if (s === 'draft') return (
      <div style={{ display: 'flex', gap: '8px' }}>
        <ActionBtn label="Start"  icon={<Play size={13} />}     action="start"  id={c.id} />
        <ActionBtn label="Delete" icon={<Trash2 size={13} />}   action="delete" id={c.id} color="#ef4444" />
      </div>
    )
    if (s === 'paused') return (
      <div style={{ display: 'flex', gap: '8px' }}>
        <ActionBtn label="Resume" icon={<RotateCcw size={13} />} action="resume" id={c.id} />
        <ActionBtn label="Stop"   icon={<Square size={13} />}    action="stop"   id={c.id} />
      </div>
    )
    return (
      <div style={{ display: 'flex', gap: '8px' }}>
        <ActionBtn label="View"   icon={<BarChart2 size={13} />} action="view"   id={c.id} />
        <ActionBtn label="Delete" icon={<Trash2 size={13} />}    action="delete" id={c.id} color="#ef4444" />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Search + Add */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          flex: 1, display: 'flex', alignItems: 'center', gap: '8px',
          backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 14px',
        }}>
          <Search size={15} style={{ color: '#9ca3af', flexShrink: 0 }} />
          <input
            type="text"
            placeholder="Search by campaign name..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            style={{ border: 'none', outline: 'none', fontSize: '14px', color: '#374151', backgroundColor: 'transparent', width: '100%' }}
          />
        </div>
        <button
          onClick={() => router.push('/campaigns/new')}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            backgroundColor: '#2563eb', color: 'white', border: 'none',
            borderRadius: '10px', padding: '10px 20px', fontSize: '14px', fontWeight: '600',
            cursor: 'pointer', whiteSpace: 'nowrap',
          }}
        >
          <Plus size={16} /> Add Campaign
        </button>
      </div>

      {/* Status filters */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {STATUS_FILTERS.map(f => (
          <button
            key={f}
            onClick={() => { setActiveFilter(f); setPage(1) }}
            style={{
              padding: '5px 16px', borderRadius: '20px', fontSize: '13px', fontWeight: '500',
              cursor: 'pointer', transition: 'all 0.15s',
              border: activeFilter === f ? '2px solid #2563eb' : '1px solid #d1d5db',
              backgroundColor: 'white',
              color: activeFilter === f ? '#2563eb' : '#6b7280',
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: '#9ca3af', fontSize: '14px' }}>Loading...</div>
        ) : (
          <>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                  {['Name', 'Status', 'Bolna Agent ID', 'Created Date', 'Actions'].map(h => (
                    <th key={h} style={{
                      textAlign: 'left', padding: '14px 20px',
                      fontSize: '14px', fontWeight: '700', color: '#111827',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {paginated.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: '60px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>
                      No campaigns found
                    </td>
                  </tr>
                ) : (
                  paginated.map((c, i) => {
                    const s = STATUS_STYLE[c.status] ?? STATUS_STYLE.draft
                    return (
                      <tr
                        key={c.id}
                        style={{ borderBottom: i < paginated.length - 1 ? '1px solid #f3f4f6' : 'none' }}
                        onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                        onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                      >
                        <td
                          style={{ padding: '14px 20px', fontSize: '14px', fontWeight: '500', color: '#111827', cursor: 'pointer' }}
                          onClick={() => router.push(`/campaigns/${c.id}`)}
                        >
                          {c.name}
                        </td>
                        <td style={{ padding: '14px 20px' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '13px', fontWeight: '600', color: s.color }}>
                            <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: s.dot, display: 'inline-block' }} />
                            {s.label}
                          </span>
                        </td>
                        <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>
                          {c.bolna_agent_id ? `${c.bolna_agent_id.slice(0, 10)}...` : '—'}
                        </td>
                        <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>
                          {fmtDate(c.created_at)}
                        </td>
                        <td style={{ padding: '14px 20px' }}>
                          {renderActions(c)}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>

            {/* Pagination */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 20px', borderTop: '1px solid #f3f4f6',
              fontSize: '13px', color: '#6b7280',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <select
                  value={pageSize}
                  onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}
                  style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', cursor: 'pointer', backgroundColor: 'white' }}
                >
                  {[10, 20, 50].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
                <span>Items per page</span>
                <span style={{ marginLeft: '8px', color: '#374151' }}>
                  {filtered.length === 0 ? '0' : `${(page - 1) * pageSize + 1}-${Math.min(page * pageSize, filtered.length)}`} of {filtered.length} items
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <select
                  value={page}
                  onChange={e => setPage(Number(e.target.value))}
                  style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', cursor: 'pointer', backgroundColor: 'white' }}
                >
                  {[...Array(totalPages)].map((_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
                </select>
                <span>of {totalPages} pages</span>
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: page === 1 ? 'not-allowed' : 'pointer', color: page === 1 ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}
                >‹</button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: page >= totalPages ? 'not-allowed' : 'pointer', color: page >= totalPages ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}
                >›</button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
