'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { walletApi } from '@/lib/api/wallet'
import { campaignsApi } from '@/lib/api/campaigns'
import { Search, SlidersHorizontal, Eye } from 'lucide-react'

interface WalletSummary {
  minutes_balance: number
  rate_per_minute: number
  total_minutes_purchased: number
  total_minutes_used: number
  total_amount_paid: number
}

interface Campaign {
  id: string
  name: string
  status: string
  total_minutes_used?: number
}

const STATUS_STYLE: Record<string, { color: string; bg: string; dot: string }> = {
  active:    { color: '#16a34a', bg: '#f0fdf4', dot: '#16a34a' },
  paused:    { color: '#d97706', bg: '#fffbeb', dot: '#d97706' },
  inactive:  { color: '#6b7280', bg: '#f3f4f6', dot: '#6b7280' },
  completed: { color: '#6b7280', bg: '#f3f4f6', dot: '#6b7280' },
}

function StatCard({ title, value, sub }: { title: string; value: string | number; sub?: string }) {
  return (
    <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '18px 20px' }}>
      <p style={{ fontSize: '13px', color: '#6b7280', fontWeight: '500', marginBottom: '8px' }}>{title}</p>
      <p style={{ fontSize: '26px', fontWeight: '700', color: '#111827', lineHeight: 1, marginBottom: sub ? '6px' : 0 }}>{value}</p>
      {sub && <p style={{ fontSize: '12px', color: '#16a34a', fontWeight: '500' }}>{sub}</p>}
    </div>
  )
}

export default function AdminDashboard() {
  const router = useRouter()
  const [wallet, setWallet] = useState<WalletSummary | null>(null)
  const [actualBalance, setActualBalance] = useState<number>(0)
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [wRes, cRes] = await Promise.all([
          walletApi.summary(),
          campaignsApi.list(),
        ])
        const w = wRes.data ?? {}
        setActualBalance(w.minutes_balance ?? 0)
        setWallet(w)
        const list = Array.isArray(cRes.data)
          ? cRes.data
          : cRes.data?.campaigns ?? cRes.data?.results ?? []
        setCampaigns(list)
      } catch {}
      setLoading(false)
    }
    fetchAll()
  }, [])

  const activeCampaigns = campaigns.filter(c => c.status === 'active').length
  const totalMinutesUsed = wallet?.total_minutes_used ?? 0
  const balance = actualBalance
  const totalPurchased = wallet?.total_minutes_purchased ?? 0
  const usagePct = totalPurchased > 0 ? Math.round((totalMinutesUsed / totalPurchased) * 100) : 0
  const remainingPct = totalPurchased > 0 ? 100 - usagePct : 100
  const isLow = totalPurchased > 0 && remainingPct <= 30 && balance > 0
  const isZero = totalPurchased > 0 && balance === 0

  const filteredCampaigns = campaigns.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase())
  ).slice(0, 5)

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '12px' }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} style={{ height: '90px', backgroundColor: '#e5e7eb', borderRadius: '12px' }} />
          ))}
        </div>
        <div style={{ height: '360px', backgroundColor: '#e5e7eb', borderRadius: '12px' }} />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Platform stats */}
      <div>
        <p style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '12px' }}>Platform stats</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          <StatCard title="Wallet Balance" value={`${balance.toLocaleString('en-IN')} min`} />
          <StatCard title="Active Campaigns" value={activeCampaigns} />
          <StatCard title="Total Campaigns" value={campaigns.length} />
          <StatCard title="Total Minutes Used" value={totalMinutesUsed.toLocaleString('en-IN')} />
        </div>
      </div>

      {/* Main content: campaigns left, wallet right */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '16px', alignItems: 'start' }}>

        {/* Recent Campaigns */}
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid #f3f4f6', flexWrap: 'wrap', gap: '10px' }}>
            <p style={{ fontSize: '15px', fontWeight: '700', color: '#111827' }}>Recent Campaigns</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', backgroundColor: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '7px 12px' }}>
                <Search size={13} style={{ color: '#9ca3af' }} />
                <input
                  type="text"
                  placeholder="Search"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  style={{ border: 'none', outline: 'none', fontSize: '13px', color: '#374151', backgroundColor: 'transparent', width: '120px' }}
                />
              </div>
              <button style={{ display: 'flex', alignItems: 'center', gap: '5px', backgroundColor: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '7px 12px', fontSize: '13px', color: '#2563eb', fontWeight: '500', cursor: 'pointer' }}>
                <SlidersHorizontal size={13} />
                Filter
              </button>
            </div>
          </div>

          {/* Table */}
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f3f4f6' }}>
                {['Campaign Name', 'Status', 'Minutes Used', 'View'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '12px 20px', fontSize: '13px', fontWeight: '700', color: '#374151' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredCampaigns.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ padding: '40px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>
                    No campaigns yet
                  </td>
                </tr>
              ) : (
                filteredCampaigns.map((c, i) => {
                  const s = STATUS_STYLE[c.status] ?? STATUS_STYLE.inactive
                  return (
                    <tr key={c.id}
                      style={{ borderBottom: i < filteredCampaigns.length - 1 ? '1px solid #f9fafb' : 'none' }}
                      onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                      onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                    >
                      <td style={{ padding: '13px 20px', fontSize: '13px', fontWeight: '600', color: '#111827' }}>{c.name}</td>
                      <td style={{ padding: '13px 20px' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '12px', fontWeight: '600', color: s.color, backgroundColor: s.bg, padding: '3px 10px', borderRadius: '20px' }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: s.dot, display: 'inline-block' }} />
                          {c.status.charAt(0).toUpperCase() + c.status.slice(1)}
                        </span>
                      </td>
                      <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>
                        {c.total_minutes_used != null ? `${c.total_minutes_used.toLocaleString('en-IN')} min` : '0 min'}
                      </td>
                      <td style={{ padding: '13px 20px' }}>
                        <button onClick={() => router.push(`/campaigns/${c.id}`)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af' }}>
                          <Eye size={16} />
                        </button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>

          {campaigns.length > 5 && (
            <div style={{ padding: '10px 20px', borderTop: '1px solid #f3f4f6', display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={() => router.push('/campaigns')}
                style={{ fontSize: '13px', color: '#6b7280', background: 'none', border: 'none', cursor: 'pointer' }}>
                View all
              </button>
            </div>
          )}
        </div>

        {/* Wallet panel */}
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '20px' }}>
          <p style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '16px' }}>Wallet</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '16px' }}>
            <div>
              <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '2px' }}>Minutes balance</p>
              <p style={{ fontSize: '20px', fontWeight: '700', color: '#111827' }}>{balance.toLocaleString('en-IN')}</p>
            </div>
            <div>
              <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '2px' }}>Rate per minute</p>
              <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827' }}>₹{wallet?.rate_per_minute?.toFixed(1) ?? '0.0'}</p>
            </div>
            <div>
              <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '2px' }}>Total minutes purchased</p>
              <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827' }}>{totalPurchased.toLocaleString('en-IN')}</p>
            </div>
            <div>
              <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '2px' }}>Total minutes used</p>
              <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827' }}>{totalMinutesUsed.toLocaleString('en-IN')}</p>
            </div>
          </div>

          {/* Usage bar — changes based on state */}
          {isZero ? (
            <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '10px', padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <p style={{ fontSize: '13px', fontWeight: '600', color: '#dc2626' }}>Usage</p>
                <p style={{ fontSize: '13px', fontWeight: '700', color: '#dc2626' }}>100%</p>
              </div>
              <div style={{ height: '6px', backgroundColor: '#fca5a5', borderRadius: '3px', overflow: 'hidden', marginBottom: '6px' }}>
                <div style={{ height: '100%', width: '100%', backgroundColor: '#ef4444', borderRadius: '3px' }} />
              </div>
              <p style={{ fontSize: '12px', color: '#dc2626' }}>Wallet balance is empty</p>
            </div>
          ) : isLow ? (
            <div style={{ backgroundColor: '#F5A623', borderRadius: '10px', padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <p style={{ fontSize: '13px', fontWeight: '600', color: 'white' }}>Usage</p>
                <p style={{ fontSize: '13px', fontWeight: '700', color: 'white' }}>{usagePct}%</p>
              </div>
              <div style={{ height: '6px', backgroundColor: 'rgba(255,255,255,0.3)', borderRadius: '3px', overflow: 'hidden', marginBottom: '6px' }}>
                <div style={{ height: '100%', width: `${usagePct}%`, backgroundColor: '#ef4444', borderRadius: '3px' }} />
              </div>
              <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.9)' }}>
                {totalMinutesUsed.toLocaleString('en-IN')} of {totalPurchased.toLocaleString('en-IN')} minutes used
              </p>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <p style={{ fontSize: '13px', fontWeight: '600', color: '#374151' }}>Usage</p>
                <p style={{ fontSize: '13px', fontWeight: '700', color: '#2563eb' }}>{usagePct}%</p>
              </div>
              <div style={{ height: '6px', backgroundColor: '#e5e7eb', borderRadius: '3px', overflow: 'hidden', marginBottom: '6px' }}>
                <div style={{ height: '100%', width: `${usagePct}%`, backgroundColor: '#2563eb', borderRadius: '3px' }} />
              </div>
              <p style={{ fontSize: '12px', color: '#6b7280' }}>
                {totalMinutesUsed.toLocaleString('en-IN')} of {totalPurchased.toLocaleString('en-IN')} minutes used
              </p>
            </div>
          )}

          <p style={{ fontSize: '12px', color: '#9ca3af', marginTop: '12px' }}>
            Contact your super admin to add more wallet credits.
          </p>
        </div>
      </div>

    </div>
  )
}
