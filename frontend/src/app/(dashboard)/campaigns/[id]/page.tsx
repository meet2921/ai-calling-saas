'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { campaignsApi } from '@/lib/api/campaigns'
import { leadsApi } from '@/lib/api/leads'
import { analyticsApi } from '@/lib/api/analytics'
import { Pause, Square, Search, SlidersHorizontal, Plus, Trash2 } from 'lucide-react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { toast } from 'sonner'

interface Campaign {
  id: string
  name: string
  status: string
  bolna_agent_id: string | null
  description: string | null
  created_at: string
}

interface AgentTask {
  tools_config?: {
    synthesizer?: { provider?: string; provider_config?: { 
    voice?: string; language?: string; model?: string } }
    transcriber?: { provider?: string; language?: string; model?: string }
    llm_agent?: { llm_config?: { model?: string; provider?: string } }
  }
}

interface Agent {
  name?: string
  description?: string
  config_summary?: string
  id?: string
  agent_name?: string
  agent_description?: string
  configuration_summary?: string
  agent_status?: string
  agent_type?: string
  agent_welcome_message?: string
  tasks?: AgentTask[]
  agent_prompts?: Record<string, { system_prompt?: string }>
}

interface Lead {
  id: string
  phone: string
  name?: string
  status: string
  last_called?: string
  duration?: number
  custom_fields?: Record<string, string>
}

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

const LEAD_STATUS: Record<string, { color: string; dot: string; label: string }> = {
  completed:  { color: '#16a34a', dot: '#16a34a', label: 'Completed' },
  failed:     { color: '#ef4444', dot: '#ef4444', label: 'Failed' },
  no_answer:  { color: '#6b7280', dot: '#9ca3af', label: 'No answer' },
  pending:    { color: '#d97706', dot: '#d97706', label: 'Pending' },
  calling:    { color: '#2563eb', dot: '#2563eb', label: 'Calling' },
  queued:     { color: '#7c3aed', dot: '#7c3aed', label: 'Queued' },
}

const TABS = ['Leads', 'Analytics', 'Call logs'] as const
type Tab = typeof TABS[number]

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [agent, setAgent] = useState<Agent | null>(null)
  const [tab, setTab] = useState<Tab>('Leads')

  // Leads
  const [leads, setLeads] = useState<Lead[]>([])
  const [leadsTotal, setLeadsTotal] = useState(0)
  const [leadsPage, setLeadsPage] = useState(1)
  const [leadsPageSize, setLeadsPageSize] = useState(20)
  const [leadsSearch, setLeadsSearch] = useState('')

  // Call logs
  const [callLogs, setCallLogs] = useState<CallLog[]>([])
  const [logsPage, setLogsPage] = useState(1)
  const [logsPageSize, setLogsPageSize] = useState(20)

  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [confirmLeadId, setConfirmLeadId] = useState<string | null>(null)
  const [selectedLog, setSelectedLog] = useState<CallLog | null>(null)
  useEffect(() => {
    if (!id) return
    Promise.all([
      campaignsApi.get(id),
      campaignsApi.getAgent(id).catch(() => ({ data: null })),
    ]).then(([cRes, aRes]) => {
      setCampaign(cRes.data)
      setAgent(aRes.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (!id || tab !== 'Leads') return
    leadsApi.list(id, leadsPage, leadsPageSize).then(res => {
      const data = res.data
      const list = Array.isArray(data) ? data : data?.leads ?? data?.results ?? []
      const total = data?.total ?? data?.count ?? list.length
      setLeads(list)
      setLeadsTotal(total)
    }).catch(() => {})
  }, [id, tab, leadsPage, leadsPageSize])

  useEffect(() => {
    if (!id || tab !== 'Call logs') return
    analyticsApi.logs(id).then(res => {
      const list = Array.isArray(res.data) ? res.data : res.data?.logs ?? res.data?.results ?? []
      setCallLogs(list)
    }).catch(() => {})
  }, [id, tab])

  const handleDeleteLead = (leadId: string) => {
    setConfirmLeadId(leadId)
  }

  const confirmDeleteLead = async () => {
    if (!id || !confirmLeadId) return
    try {
      await leadsApi.delete(id, confirmLeadId)
      setLeads(prev => prev.filter(l => l.id !== confirmLeadId))
      setLeadsTotal(prev => prev - 1)
      toast.success('Lead deleted')
    } catch {
      toast.error('Failed to delete lead')
    } finally {
      setConfirmLeadId(null)
    }
  }

  const handleCampaignAction = async (action: 'pause' | 'stop') => {
    if (!id) return
    setActionLoading(true)
    try {
      if (action === 'pause') await campaignsApi.pause(id)
      else await campaignsApi.stop(id)
      const res = await campaignsApi.get(id)
      setCampaign(res.data)
      toast.success(`Campaign ${action === 'pause' ? 'paused' : 'stopped'}`)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'string'
        ? detail
        : typeof detail === 'object' && detail?.message
          ? detail.message
          : 'Action failed'
      toast.error(msg)
    } finally {
      setActionLoading(false)
    }
  }

  const fmtDate = (d: string) =>
    new Date(d).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Calcutta' })

  const fmtDuration = (sec: number) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0')
    const s = (sec % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  const filteredLeads = leads.filter(l => {
    const name = l.name ?? l.custom_fields?.name ?? ''
    return name.toLowerCase().includes(leadsSearch.toLowerCase()) ||
      l.phone.includes(leadsSearch)
  })

  const leadsTotal2 = leadsSearch ? filteredLeads.length : leadsTotal
  const totalLeadsPages = Math.max(1, Math.ceil(leadsTotal2 / leadsPageSize))
  const totalLogsPages = Math.max(1, Math.ceil(callLogs.length / logsPageSize))
  const paginatedLogs = callLogs.slice((logsPage - 1) * logsPageSize, logsPage * logsPageSize)

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {[...Array(3)].map((_, i) => (
          <div key={i} style={{ height: '100px', backgroundColor: '#e5e7eb', borderRadius: '12px' }} />
        ))}
      </div>
    )
  }

  if (!campaign) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>Campaign not found</div>
  }

  const isRunning = campaign.status === 'running' || campaign.status === 'active'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#9ca3af' }}>
        <span
          style={{ cursor: 'pointer', color: '#6b7280' }}
          onClick={() => router.push('/campaigns')}
        >Campaigns</span>
        <span>›</span>
        <span style={{ color: '#374151' }}>{campaign.name}</span>
      </div>

      {/* Title row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#111827', margin: 0 }}>
          {campaign.name}
        </h1>
        <div style={{ display: 'flex', gap: '10px', flexShrink: 0 }}>
          <button
            onClick={() => handleCampaignAction('pause')}
            disabled={actionLoading || !isRunning}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '8px 18px', borderRadius: '8px', fontSize: '13px', fontWeight: '600',
              border: '1px solid #2563eb', color: '#2563eb', backgroundColor: 'white',
              cursor: isRunning ? 'pointer' : 'not-allowed',
              opacity: isRunning ? 1 : 0.4,
            }}
          >
            <Pause size={14} /> Pause
          </button>
          <button
            onClick={() => handleCampaignAction('stop')}
            disabled={actionLoading || campaign.status === 'stopped' || campaign.status === 'completed'}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '8px 18px', borderRadius: '8px', fontSize: '13px', fontWeight: '600',
              border: '1px solid #2563eb', color: '#2563eb', backgroundColor: 'white',
              cursor: (campaign.status === 'stopped' || campaign.status === 'completed') ? 'not-allowed' : 'pointer',
              opacity: (campaign.status === 'stopped' || campaign.status === 'completed') ? 0.4 : 1,
            }}
          >
            <Square size={14} /> Stop
          </button>
        </div>
      </div>

      {/* Campaign details */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '20px 24px' }}>
        <p style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '20px' }}>Campaign details</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
          <div>
            <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '3px' }}>Campaign name</p>
            <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>{campaign.name}</p>
          </div>
          <div>
            <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '3px' }}>Created date</p>
            <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>
              {new Date(campaign.created_at).toLocaleDateString('en-IN', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'Asia/Calcutta' })}
            </p>
          </div>
          <div>
            <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '3px' }}>Bolna Agent ID</p>
            <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827', wordBreak: 'break-all' }}>{campaign.bolna_agent_id ?? '—'}</p>
          </div>
          {campaign.description && (
            <div style={{ gridColumn: '1 / -1' }}>
              <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '3px' }}>Campaign description</p>
              <p style={{ fontSize: '14px', color: '#374151', lineHeight: '1.5' }}>{campaign.description}</p>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div>
        <div style={{ display: 'flex', gap: '0', borderBottom: '1px solid #e5e7eb' }}>
          {TABS.map(t => {
            const tabRoute = t === 'Analytics' ? `/campaigns/${id}/analytics`
              : t === 'Call logs' ? `/campaigns/${id}/call-logs`
              : null
            return (
              <button
                key={t}
                onClick={() => tabRoute ? router.push(tabRoute) : setTab(t)}
                style={{
                  padding: '10px 20px', fontSize: '14px', fontWeight: tab === t ? '600' : '400',
                  color: tab === t ? '#2563eb' : '#6b7280',
                  background: 'none', border: 'none', cursor: 'pointer',
                  borderBottom: tab === t ? '2px solid #2563eb' : '2px solid transparent',
                  marginBottom: '-1px',
                }}
              >
                {t}
              </button>
            )
          })}
        </div>

        {/* Leads Tab */}
        {tab === 'Leads' && (
          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Toolbar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                flex: 1, display: 'flex', alignItems: 'center', gap: '8px',
                backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '9px 14px',
              }}>
                <Search size={14} style={{ color: '#9ca3af' }} />
                <input
                  type="text"
                  placeholder="Search leads..."
                  value={leadsSearch}
                  onChange={e => setLeadsSearch(e.target.value)}
                  style={{ border: 'none', outline: 'none', fontSize: '13px', color: '#374151', backgroundColor: 'transparent', width: '100%' }}
                />
              </div>
              <button style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                backgroundColor: 'white', border: '1px solid #e5e7eb',
                borderRadius: '10px', padding: '9px 14px', fontSize: '13px', fontWeight: '500',
                color: '#2563eb', cursor: 'pointer',
              }}>
                <SlidersHorizontal size={14} /> Filter
              </button>
              <button
                onClick={() => router.push(`/campaigns/${id}/leads`)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  backgroundColor: '#2563eb', color: 'white', border: 'none',
                  borderRadius: '10px', padding: '9px 20px', fontSize: '13px', fontWeight: '600',
                  cursor: 'pointer', whiteSpace: 'nowrap',
                }}
              >
                <Plus size={15} /> Add Leads
              </button>
            </div>

            {/* Leads table */}
            <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                    {['Name', 'Status', 'Phone number', 'Last Called', 'Duration', ''].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '13px 20px', fontSize: '14px', fontWeight: '700', color: '#111827' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(leadsSearch ? filteredLeads : leads).length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ padding: '60px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>
                        No leads yet. Upload a CSV to get started.
                      </td>
                    </tr>
                  ) : (
                    (leadsSearch ? filteredLeads : leads).map((l, i) => {
                      const name = l.name ?? l.custom_fields?.name ?? '—'
                      const s = LEAD_STATUS[l.status] ?? LEAD_STATUS.pending
                      return (
                        <tr
                          key={l.id}
                          style={{ borderBottom: i < leads.length - 1 ? '1px solid #f3f4f6' : 'none' }}
                          onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                          onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                        >
                          <td style={{ padding: '13px 20px', fontSize: '14px', fontWeight: '500', color: '#111827' }}>{name}</td>
                          <td style={{ padding: '13px 20px' }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '13px', fontWeight: '600', color: s.color }}>
                              <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: s.dot, display: 'inline-block' }} />
                              {s.label}
                            </span>
                          </td>
                          <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>{l.phone}</td>
                          <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>
                            {l.last_called ? fmtDate(l.last_called) : '—'}
                          </td>
                          <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>
                            {l.duration != null ? fmtDuration(l.duration) : '—'}
                          </td>
                          <td style={{ padding: '13px 20px', textAlign: 'right' }}>
                            <button
                              onClick={() => handleDeleteLead(l.id)}
                              title="Delete lead"
                              style={{
                                background: 'none', border: 'none', cursor: 'pointer',
                                color: '#9ca3af', padding: '4px', borderRadius: '6px',
                                display: 'inline-flex', alignItems: 'center',
                              }}
                              onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = '#ef4444'}
                              onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = '#9ca3af'}
                            >
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>

              {/* Leads pagination */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '12px 20px', borderTop: '1px solid #f3f4f6',
                fontSize: '13px', color: '#6b7280',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <select
                    value={leadsPageSize}
                    onChange={e => { setLeadsPageSize(Number(e.target.value)); setLeadsPage(1) }}
                    style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}
                  >
                    {[20, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                  <span>Items per page</span>
                  <span style={{ marginLeft: '8px', color: '#374151' }}>
                    {leadsTotal2 === 0 ? '0' : `${(leadsPage - 1) * leadsPageSize + 1}-${Math.min(leadsPage * leadsPageSize, leadsTotal2)}`} of {leadsTotal2} items
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <select
                    value={leadsPage}
                    onChange={e => setLeadsPage(Number(e.target.value))}
                    style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}
                  >
                    {[...Array(totalLeadsPages)].map((_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
                  </select>
                  <span>of {totalLeadsPages} pages</span>
                  <button
                    onClick={() => setLeadsPage(p => Math.max(1, p - 1))}
                    disabled={leadsPage === 1}
                    style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: leadsPage === 1 ? 'not-allowed' : 'pointer', color: leadsPage === 1 ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}
                  >‹</button>
                  <button
                    onClick={() => setLeadsPage(p => Math.min(totalLeadsPages, p + 1))}
                    disabled={leadsPage >= totalLeadsPages}
                    style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: leadsPage >= totalLeadsPages ? 'not-allowed' : 'pointer', color: leadsPage >= totalLeadsPages ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}
                  >›</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {tab === 'Analytics' && (
          <div style={{ marginTop: '16px' }}>
            <AnalyticsTab campaignId={id} />
          </div>
        )}

        {/* Call Logs Tab */}
        {tab === 'Call logs' && (
          <div style={{ marginTop: '16px' }}>
            <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                    {['Phone number', 'Outcome', 'Duration', 'Sentiment', 'Appointment', 'Started At', ''].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '13px 20px', fontSize: '14px', fontWeight: '700', color: '#111827' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {paginatedLogs.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ padding: '60px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>
                        No call logs yet
                      </td>
                    </tr>
                  ) : (
                    paginatedLogs.map((log, i) => {
                      const sentimentColor = log.customer_sentiment === 'positive' ? '#16a34a'
                        : log.customer_sentiment === 'negative' ? '#ef4444' : '#6b7280'
                      return (
                        <tr
                          key={log.id}
                          style={{ borderBottom: i < paginatedLogs.length - 1 ? '1px solid #f3f4f6' : 'none', cursor: 'pointer' }}
                          onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                          onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                          onClick={() => setSelectedLog(log)}
                        >
                          <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>{log.user_number ?? '—'}</td>
                          <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>{log.status ?? '—'}</td>
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
              {/* Logs pagination */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', borderTop: '1px solid #f3f4f6', fontSize: '13px', color: '#6b7280' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <select
                    value={logsPageSize}
                    onChange={e => { setLogsPageSize(Number(e.target.value)); setLogsPage(1) }}
                    style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}
                  >
                    {[20, 50].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                  <span>Items per page</span>
                  <span style={{ marginLeft: '8px', color: '#374151' }}>{callLogs.length} items</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <select
                    value={logsPage}
                    onChange={e => setLogsPage(Number(e.target.value))}
                    style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}
                  >
                    {[...Array(totalLogsPages)].map((_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
                  </select>
                  <span>of {totalLogsPages} pages</span>
                  <button onClick={() => setLogsPage(p => Math.max(1, p - 1))} disabled={logsPage === 1}
                    style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: logsPage === 1 ? 'not-allowed' : 'pointer', color: logsPage === 1 ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}>‹</button>
                  <button onClick={() => setLogsPage(p => Math.min(totalLogsPages, p + 1))} disabled={logsPage >= totalLogsPages}
                    style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: logsPage >= totalLogsPages ? 'not-allowed' : 'pointer', color: logsPage >= totalLogsPages ? '#d1d5db' : '#374151', backgroundColor: 'white', fontSize: '16px' }}>›</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Call Log Detail Drawer */}
      {selectedLog && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          backgroundColor: 'rgba(0,0,0,0.4)',
          display: 'flex', justifyContent: 'flex-end',
        }} onClick={() => setSelectedLog(null)}>
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: '480px', height: '100%', backgroundColor: 'white',
              overflowY: 'auto', display: 'flex', flexDirection: 'column',
              boxShadow: '-8px 0 30px rgba(0,0,0,0.12)',
            }}
          >
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
                  { label: 'Outcome', value: selectedLog.status ?? '—' },
                  { label: 'Duration', value: selectedLog.duration ? fmtDuration(selectedLog.duration) : '—' },
                  { label: 'Started At', value: fmtDate(selectedLog.executed_at) },
                  { label: 'Hangup By', value: selectedLog.transfer_call ? 'Transferred' : '—' },
                ].map(({ label, value }) => (
                  <div key={label} style={{ backgroundColor: '#f9fafb', borderRadius: '8px', padding: '12px' }}>
                    <p style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</p>
                    <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>{value}</p>
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
                    {selectedLog.appointment_date && (
                      <p style={{ fontSize: '13px', color: '#374151' }}>{fmtDate(selectedLog.appointment_date)}</p>
                    )}
                    {selectedLog.appointment_mode && (
                      <p style={{ fontSize: '13px', color: '#6b7280', textTransform: 'capitalize' }}>{selectedLog.appointment_mode}</p>
                    )}
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

      {/* Delete lead confirmation modal */}
      {confirmLeadId && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          backgroundColor: 'rgba(0,0,0,0.45)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            backgroundColor: 'white', borderRadius: '16px',
            padding: '32px', width: '100%', maxWidth: '420px',
            boxShadow: '0 25px 60px rgba(0,0,0,0.18)',
            display: 'flex', flexDirection: 'column', gap: '20px',
          }}>
            {/* Icon + title */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
              <div style={{
                width: '44px', height: '44px', borderRadius: '50%',
                backgroundColor: '#fee2e2', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <Trash2 size={20} color="#ef4444" />
              </div>
              <div>
                <p style={{ fontSize: '16px', fontWeight: '700', color: '#111827', marginBottom: '6px' }}>Delete lead?</p>
                <p style={{ fontSize: '13px', color: '#6b7280', lineHeight: '1.6' }}>
                  This action cannot be undone. The lead will be permanently removed from this campaign.
                </p>
              </div>
            </div>
            {/* Buttons */}
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setConfirmLeadId(null)}
                style={{
                  padding: '9px 20px', borderRadius: '8px', fontSize: '13px', fontWeight: '600',
                  border: '1px solid #e5e7eb', backgroundColor: 'white', color: '#374151', cursor: 'pointer',
                }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'white'}
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteLead}
                style={{
                  padding: '9px 20px', borderRadius: '8px', fontSize: '13px', fontWeight: '600',
                  border: 'none', backgroundColor: '#ef4444', color: 'white', cursor: 'pointer',
                }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#dc2626'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#ef4444'}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function AnalyticsTab({ campaignId }: { campaignId: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    analyticsApi.get(campaignId)
      .then(res => setData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [campaignId])

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>Loading analytics...</div>
  if (!data) return <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>No analytics available</div>

  const stats = [
    { label: 'Total Calls', value: data.total_calls ?? 0 },
    { label: 'Completed', value: data.completed_calls ?? 0 },
    { label: 'Failed', value: data.failed_calls ?? 0 },
    { label: 'Avg Duration', value: `${data.avg_duration ?? 0}s` },
    { label: 'Total Duration', value: `${data.total_duration ?? 0} min` },
  ]

  const callsByDay: { date: string; calls: number }[] = data.calls_by_day ?? []
  const minutesByDay: { date: string; minutes: number }[] = data.minutes_by_day ?? []

  const cardStyle: React.CSSProperties = {
    backgroundColor: 'white', border: '1px solid #e5e7eb',
    borderRadius: '12px', padding: '20px',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
        {stats.map(s => (
          <div key={s.label} style={cardStyle}>
            <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>{s.label}</p>
            <p style={{ fontSize: '24px', fontWeight: '700', color: '#111827' }}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

        {/* Calls over time */}
        <div style={cardStyle}>
          <p style={{ fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '16px' }}>Calls Over Time</p>
          {callsByDay.length === 0 ? (
            <div style={{ height: '180px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: '13px' }}>No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={callsByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip formatter={(v: any) => [v, 'Calls']} labelFormatter={l => `Date: ${l}`} />
                <Line type="monotone" dataKey="calls" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Minutes per day */}
        <div style={cardStyle}>
          <p style={{ fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '16px' }}>Minutes Per Day</p>
          {minutesByDay.length === 0 ? (
            <div style={{ height: '180px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: '13px' }}>No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={minutesByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: any) => [v, 'Minutes']} labelFormatter={l => `Date: ${l}`} />
                <Bar dataKey="minutes" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

      </div>
    </div>
  )
}
