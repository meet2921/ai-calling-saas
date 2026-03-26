'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { campaignsApi } from '@/lib/api/campaigns'
import { analyticsApi } from '@/lib/api/analytics'

interface Campaign { id: string; name: string }

interface CallLog {
  id: string
  user_number?: string
  duration: number
  status: string | null
  executed_at: string
  cost?: number
  summary?: string | null
  final_call_summary?: string | null
  transcript?: string | null
  recording_url?: string | null
  customer_sentiment?: string | null
  interest_level?: string | null
  appointment_booked?: boolean
  appointment_date?: string | null
  appointment_mode?: string | null
  transfer_call?: boolean
}

const OUTCOME_STYLE: Record<string, { bg: string; color: string; dot?: string }> = {
  connected:  { bg: '#dcfce7', color: '#16a34a', dot: '#16a34a' },
  completed:  { bg: '#dcfce7', color: '#16a34a', dot: '#16a34a' },
  failed:     { bg: '#fee2e2', color: '#ef4444', dot: '#ef4444' },
  no_answer:  { bg: '#f3f4f6', color: '#6b7280' },
  busy:       { bg: '#fef9c3', color: '#ca8a04', dot: '#ca8a04' },
  initiated:  { bg: '#eff6ff', color: '#2563eb', dot: '#2563eb' },
}

function OutcomeBadge({ status }: { status: string | null }) {
  const s = status?.toLowerCase() ?? ''
  const style = OUTCOME_STYLE[s] ?? { bg: '#f3f4f6', color: '#6b7280' }
  const label = s === 'no_answer' ? 'No answer' : s.charAt(0).toUpperCase() + s.slice(1)
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      padding: '3px 10px', borderRadius: '20px',
      backgroundColor: style.bg, color: style.color,
      fontSize: '12px', fontWeight: '500',
    }}>
      {style.dot && <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: style.dot, flexShrink: 0 }} />}
      {label || '—'}
    </span>
  )
}

const fmtDuration = (sec: number) => {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}m ${s}s`
}

const fmtDate = (d: string) =>
  new Date(d).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: true,
  })

export default function CallLogsPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [logs, setLogs] = useState<CallLog[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedLog, setSelectedLog] = useState<CallLog | null>(null)

  useEffect(() => {
    if (!id) return
    Promise.all([campaignsApi.get(id), analyticsApi.logs(id)])
      .then(([campRes, logsRes]) => {
        setCampaign(campRes.data)
        const data = logsRes.data
        setLogs(Array.isArray(data) ? data : data?.logs ?? data?.results ?? [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>Loading call logs...</div>

  const total = logs.length
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const paginated = logs.slice((page - 1) * pageSize, page * pageSize)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#9ca3af' }}>
        <span style={{ cursor: 'pointer', color: '#6b7280' }} onClick={() => router.push('/campaigns')}>Campaigns</span>
        <span>›</span>
        <span style={{ cursor: 'pointer', color: '#6b7280' }} onClick={() => router.push(`/campaigns/${id}`)}>{campaign?.name ?? '...'}</span>
        <span>›</span>
        <span style={{ color: '#374151' }}>Call logs</span>
      </div>

      <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#111827', margin: 0 }}>{campaign?.name ?? '...'}</h1>

      {/* Table */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
              {['Phone number', 'Outcome', 'Duration', 'Sentiment', 'Appointment', 'Started at', ''].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '14px', fontWeight: '700', color: '#111827' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: '60px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>No call logs yet</td>
              </tr>
            ) : (
              paginated.map((log, i) => {
                const sentimentColor = log.customer_sentiment === 'positive' ? '#16a34a'
                  : log.customer_sentiment === 'negative' ? '#ef4444' : '#6b7280'
                return (
                  <tr
                    key={log.id}
                    onClick={() => setSelectedLog(log)}
                    style={{ borderBottom: i < paginated.length - 1 ? '1px solid #f3f4f6' : 'none', cursor: 'pointer' }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                  >
                    <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151', fontWeight: '500' }}>{log.user_number ?? '—'}</td>
                    <td style={{ padding: '13px 20px' }}><OutcomeBadge status={log.status} /></td>
                    <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>{log.duration ? fmtDuration(log.duration) : '—'}</td>
                    <td style={{ padding: '13px 20px', fontSize: '13px', fontWeight: '600', color: sentimentColor, textTransform: 'capitalize' }}>
                      {log.customer_sentiment ?? '—'}
                    </td>
                    <td style={{ padding: '13px 20px', fontSize: '13px' }}>
                      {log.appointment_booked
                        ? <span style={{ color: '#16a34a', fontWeight: '600' }}>✓ Booked</span>
                        : <span style={{ color: '#9ca3af' }}>—</span>}
                    </td>
                    <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>{fmtDate(log.executed_at)}</td>
                    <td style={{ padding: '13px 20px', fontSize: '13px', color: '#2563eb' }}>Details →</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>

        {/* Pagination */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', borderTop: '1px solid #f3f4f6', fontSize: '13px', color: '#6b7280' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <select value={pageSize} onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}
              style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}>
              {[25, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
            <span>Items per page</span>
            <span style={{ marginLeft: '8px', color: '#374151' }}>
              {total === 0 ? '0' : `${(page - 1) * pageSize + 1}-${Math.min(page * pageSize, total)}`} of {total} items
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <select value={page} onChange={e => setPage(Number(e.target.value))}
              style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}>
              {[...Array(totalPages)].map((_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
            </select>
            <span>of {totalPages} pages</span>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: page === 1 ? 'not-allowed' : 'pointer', color: page === 1 ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}>‹</button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
              style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: page >= totalPages ? 'not-allowed' : 'pointer', color: page >= totalPages ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}>›</button>
          </div>
        </div>
      </div>

      {/* Detail Drawer */}
      {selectedLog && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 1000, backgroundColor: 'rgba(0,0,0,0.4)', display: 'flex', justifyContent: 'flex-end' }}
          onClick={() => setSelectedLog(null)}>
          <div onClick={e => e.stopPropagation()} style={{
            width: '480px', height: '100%', backgroundColor: 'white',
            overflowY: 'auto', display: 'flex', flexDirection: 'column',
            boxShadow: '-8px 0 30px rgba(0,0,0,0.12)',
          }}>
            {/* Header */}
            <div style={{ padding: '24px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ fontSize: '16px', fontWeight: '700', color: '#111827' }}>Call Details</p>
                <p style={{ fontSize: '13px', color: '#6b7280', marginTop: '2px' }}>{selectedLog.user_number ?? '—'}</p>
              </div>
              <button onClick={() => setSelectedLog(null)} style={{ border: 'none', background: 'none', fontSize: '22px', color: '#9ca3af', cursor: 'pointer', lineHeight: 1 }}>×</button>
            </div>

            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

              {/* Key stats */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                {[
                  { label: 'Outcome', value: <OutcomeBadge status={selectedLog.status} /> },
                  { label: 'Duration', value: selectedLog.duration ? fmtDuration(selectedLog.duration) : '—' },
                  { label: 'Started At', value: fmtDate(selectedLog.executed_at) },
                  { label: 'Hangup By', value: selectedLog.transfer_call ? 'Transferred' : '—' },
                ].map(({ label, value }) => (
                  <div key={label} style={{ backgroundColor: '#f9fafb', borderRadius: '8px', padding: '12px' }}>
                    <p style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</p>
                    <div style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>{value}</div>
                  </div>
                ))}
              </div>

              {/* Sentiment & Interest */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ backgroundColor: '#f9fafb', borderRadius: '8px', padding: '12px' }}>
                  <p style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sentiment</p>
                  <p style={{
                    fontSize: '14px', fontWeight: '600', textTransform: 'capitalize',
                    color: selectedLog.customer_sentiment === 'positive' ? '#16a34a'
                      : selectedLog.customer_sentiment === 'negative' ? '#ef4444' : '#374151',
                  }}>
                    {selectedLog.customer_sentiment ?? '—'}
                  </p>
                </div>
                <div style={{ backgroundColor: '#f9fafb', borderRadius: '8px', padding: '12px' }}>
                  <p style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Interest Level</p>
                  <p style={{ fontSize: '14px', fontWeight: '600', color: '#374151', textTransform: 'capitalize' }}>{selectedLog.interest_level ?? '—'}</p>
                </div>
              </div>

              {/* Appointment */}
              <div style={{ backgroundColor: '#f9fafb', borderRadius: '8px', padding: '12px' }}>
                <p style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Appointment</p>
                {selectedLog.appointment_booked ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <p style={{ fontSize: '14px', fontWeight: '600', color: '#16a34a' }}>✓ Booked</p>
                    {selectedLog.appointment_date && <p style={{ fontSize: '13px', color: '#374151' }}>{fmtDate(selectedLog.appointment_date)}</p>}
                    {selectedLog.appointment_mode && <p style={{ fontSize: '13px', color: '#6b7280', textTransform: 'capitalize' }}>{selectedLog.appointment_mode}</p>}
                  </div>
                ) : (
                  <p style={{ fontSize: '14px', color: '#9ca3af' }}>Not booked</p>
                )}
              </div>

              {/* Recording */}
              {selectedLog.recording_url && (
                <div>
                  <p style={{ fontSize: '12px', fontWeight: '600', color: '#374151', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Recording</p>
                  <audio controls src={selectedLog.recording_url} style={{ width: '100%', borderRadius: '8px' }} />
                </div>
              )}

              {/* Summary */}
              {(selectedLog.final_call_summary || selectedLog.summary) && (
                <div>
                  <p style={{ fontSize: '12px', fontWeight: '600', color: '#374151', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Summary</p>
                  <p style={{ fontSize: '13px', color: '#374151', lineHeight: '1.6', backgroundColor: '#f9fafb', padding: '12px', borderRadius: '8px' }}>
                    {selectedLog.final_call_summary ?? selectedLog.summary}
                  </p>
                </div>
              )}

              {/* Transcript */}
              {selectedLog.transcript && (
                <div>
                  <p style={{ fontSize: '12px', fontWeight: '600', color: '#374151', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Transcript</p>
                  <pre style={{
                    fontSize: '12px', color: '#374151', lineHeight: '1.7',
                    backgroundColor: '#f9fafb', padding: '12px', borderRadius: '8px',
                    whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
                    maxHeight: '320px', overflowY: 'auto',
                  }}>
                    {selectedLog.transcript}
                  </pre>
                </div>
              )}

            </div>
          </div>
        </div>
      )}

    </div>
  )
}
