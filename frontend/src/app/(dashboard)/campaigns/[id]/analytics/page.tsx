'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { campaignsApi } from '@/lib/api/campaigns'
import { analyticsApi } from '@/lib/api/analytics'
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

interface Campaign { id: string; name: string; status: string }

const DONUT_COLORS = ['#2563eb', '#22c55e', '#f97316', '#ef4444']
const DONUT_LABELS = ['Connected', 'No answer', 'Busy', 'Failed']

const fmtDuration = (sec: number) => {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}m ${s}s`
}

export default function CampaignAnalyticsPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [analytics, setAnalytics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  // Date range state (display only for now)
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date()
    d.setDate(1)
    return d.toISOString().slice(0, 10)
  })
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().slice(0, 10))

  useEffect(() => {
    if (!id) return
    Promise.all([
      campaignsApi.get(id),
      analyticsApi.get(id),
    ])
      .then(([campRes, analyticsRes]) => {
        setCampaign(campRes.data)
        setAnalytics(analyticsRes.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>Loading analytics...</div>
  }

  const totalCalls = analytics?.total_calls ?? 0
  const connectedCalls = analytics?.completed_calls ?? analytics?.successful_calls ?? analytics?.connected_calls ?? 0
  const avgDuration = analytics?.avg_duration ?? analytics?.average_duration ?? 0
  const totalMinutes = analytics?.total_duration ?? analytics?.total_minutes ?? 0
  const successRate = totalCalls > 0 ? Math.round((connectedCalls / totalCalls) * 100) : 0

  // Build chart-friendly arrays from API data or fall back to empty
  const callsOverTime: { date: string; calls: number }[] = analytics?.calls_by_day ?? []
  const minutesPerDay: { date: string; minutes: number }[] = analytics?.minutes_by_day ?? []
  const durationDist: { range: string; calls: number }[] = analytics?.duration_distribution ?? []

  const donutData = [
    { name: 'Connected', value: analytics?.connected_calls ?? connectedCalls },
    { name: 'No answer', value: analytics?.no_answer_calls ?? 0 },
    { name: 'Busy', value: analytics?.busy_calls ?? 0 },
    { name: 'Failed', value: analytics?.failed_calls ?? 0 },
  ].filter(d => d.value > 0)

  const statCards = [
    {
      label: 'Total calls made',
      value: totalCalls.toLocaleString(),
      sub: analytics?.calls_change != null ? `${analytics.calls_change > 0 ? '+' : ''}${analytics.calls_change}% from last month` : null,
      subColor: '#16a34a',
    },
    {
      label: 'Connected calls',
      value: connectedCalls.toLocaleString(),
      sub: `${successRate}% Success rate`,
      subColor: '#6b7280',
    },
    {
      label: 'Average Call Duration',
      value: fmtDuration(avgDuration),
      sub: analytics?.duration_change != null ? `${analytics.duration_change > 0 ? '+' : ''}${analytics.duration_change}` : null,
      subColor: '#16a34a',
    },
    {
      label: 'Total Minutes Consumed',
      value: totalMinutes.toLocaleString(),
      sub: totalMinutes > 0 ? `${(totalMinutes / 60).toFixed(1)} hours` : null,
      subColor: '#6b7280',
    },
  ]

  const inputStyle: React.CSSProperties = {
    padding: '8px 14px',
    border: '1px solid #e5e7eb',
    borderRadius: '10px',
    fontSize: '13px',
    color: '#374151',
    backgroundColor: 'white',
    outline: 'none',
    cursor: 'pointer',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#9ca3af' }}>
        <span style={{ cursor: 'pointer', color: '#6b7280' }} onClick={() => router.push('/campaigns')}>Campaigns</span>
        <span>›</span>
        <span style={{ cursor: 'pointer', color: '#6b7280' }} onClick={() => router.push(`/campaigns/${id}`)}>{campaign?.name ?? '...'}</span>
        <span>›</span>
        <span style={{ color: '#374151' }}>Analytics</span>
      </div>

      {/* Title */}
      <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#111827', margin: 0 }}>
        {campaign?.name ?? '...'}
      </h1>

      {/* Date range */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={inputStyle} />
        <span style={{ color: '#9ca3af' }}>—</span>
        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={inputStyle} />
      </div>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        {statCards.map(card => (
          <div key={card.label} style={{
            backgroundColor: 'white', border: '1px solid #e5e7eb',
            borderRadius: '14px', padding: '20px 22px',
          }}>
            <p style={{ fontSize: '13px', color: '#6b7280', margin: '0 0 10px' }}>{card.label}</p>
            <p style={{ fontSize: '28px', fontWeight: '700', color: '#111827', margin: '0 0 6px' }}>{card.value}</p>
            {card.sub && (
              <p style={{ fontSize: '12px', color: card.subColor, margin: 0 }}>{card.sub}</p>
            )}
          </div>
        ))}
      </div>

      {/* Charts row 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

        {/* Calls over time */}
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', padding: '20px 22px' }}>
          <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827', margin: '0 0 20px' }}>Calls over time</p>
          {callsOverTime.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={callsOverTime} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }}
                  cursor={{ stroke: '#2563eb', strokeDasharray: '4 4' }}
                />
                <Line
                  type="monotone" dataKey="calls" stroke="#2563eb" strokeWidth={2}
                  dot={false} activeDot={{ r: 5, fill: '#2563eb' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d1d5db', fontSize: '13px' }}>
              No data available
            </div>
          )}
        </div>

        {/* Call outcomes donut */}
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', padding: '20px 22px' }}>
          <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827', margin: '0 0 20px' }}>Call outcomes</p>
          {donutData.length > 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
              <ResponsiveContainer width="60%" height={200}>
                <PieChart>
                  <Pie
                    data={donutData} cx="50%" cy="50%"
                    innerRadius={55} outerRadius={80}
                    paddingAngle={2} dataKey="value"
                  >
                    {donutData.map((_, i) => (
                      <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {donutData.map((d, i) => {
                  const pct = totalCalls > 0 ? Math.round((d.value / totalCalls) * 100) : 0
                  return (
                    <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: DONUT_COLORS[i % DONUT_COLORS.length], flexShrink: 0 }} />
                      <div>
                        <span style={{ fontSize: '13px', fontWeight: '600', color: DONUT_COLORS[i % DONUT_COLORS.length] }}>{pct}%</span>
                        <span style={{ fontSize: '12px', color: '#6b7280', marginLeft: '4px' }}>{d.name}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d1d5db', fontSize: '13px' }}>
              No data available
            </div>
          )}
        </div>
      </div>

      {/* Charts row 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

        {/* Duration distribution */}
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', padding: '20px 22px' }}>
          <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827', margin: '0 0 20px' }}>Duration distribution</p>
          {durationDist.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={durationDist} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                <Bar dataKey="calls" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d1d5db', fontSize: '13px' }}>
              No data available
            </div>
          )}
        </div>

        {/* Minutes per day */}
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', padding: '20px 22px' }}>
          <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827', margin: '0 0 20px' }}>Minutes per day</p>
          {minutesPerDay.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={minutesPerDay} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                <Area
                  type="monotone" dataKey="minutes" stroke="#22c55e" strokeWidth={2}
                  fill="url(#greenGrad)" dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d1d5db', fontSize: '13px' }}>
              No data available
            </div>
          )}
        </div>
      </div>

    </div>
  )
}
