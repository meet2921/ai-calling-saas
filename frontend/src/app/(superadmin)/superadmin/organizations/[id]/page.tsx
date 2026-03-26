'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { adminApi } from '@/lib/api/admin'
import { Pencil, Trash2, Search, SlidersHorizontal, X, CreditCard, Users, Rocket, Phone, Clock } from 'lucide-react'
import { toast } from 'sonner'

// ─── Types ────────────────────────────────────────────────────────────────────

interface OrgDetail {
  id: string; name: string; slug: string; is_active: boolean; created_at: string
  stats: { total_users: number; total_campaigns: number; total_calls: number; total_minutes: number }
  wallet: { minutes_balance: number; rate_per_minute: number; total_amount_paid: number; total_minutes_used: number }
  users: UserRow[]
  campaigns: CampaignRow[]
}

interface UserRow {
  id: string; first_name: string; last_name: string; email: string
  role: string; is_active: boolean; last_login_at?: string
}

interface CampaignRow {
  id: string; name: string; status: string
  stats: { total_leads: number; total_calls: number; total_minutes: number }
}

interface WalletData {
  wallet: { minutes_balance: number; rate_per_minute: number; total_amount_paid: number } | null
  transactions: TxRow[]
  total_transactions: number
}

interface TxRow {
  id: string; type: string; minutes: number; amount_inr: number
  balance_after: number; description: string; created_at: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(iso?: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Calcutta' })
}

function fmtDateTime(iso?: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Calcutta' })
}

function Pagination({
  page, perPage, total,
  onPage, onPerPage,
}: { page: number; perPage: number; total: number; onPage: (p: number) => void; onPerPage: (n: number) => void }) {
  const totalPages = Math.max(1, Math.ceil(total / perPage))
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', borderTop: '1px solid #f3f4f6', flexWrap: 'wrap', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <select value={perPage} onChange={e => { onPerPage(Number(e.target.value)); onPage(1) }}
          style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '4px 8px', fontSize: '13px', color: '#374151', backgroundColor: 'white', outline: 'none', cursor: 'pointer' }}>
          {[10, 20, 50].map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        <span style={{ fontSize: '13px', color: '#6b7280' }}>Items per page</span>
        <span style={{ fontSize: '13px', color: '#6b7280', marginLeft: '8px' }}>
          {Math.min((page - 1) * perPage + 1, total)}–{Math.min(page * perPage, total)} of {total} items
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <select value={page} onChange={e => onPage(Number(e.target.value))}
          style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '4px 8px', fontSize: '13px', color: '#374151', backgroundColor: 'white', outline: 'none', cursor: 'pointer' }}>
          {[...Array(totalPages)].map((_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
        </select>
        <span style={{ fontSize: '13px', color: '#6b7280' }}>of {totalPages} pages</span>
        {(['‹', '›'] as const).map((arrow, idx) => (
          <button key={arrow} onClick={() => onPage(idx === 0 ? Math.max(1, page - 1) : Math.min(totalPages, page + 1))}
            disabled={idx === 0 ? page === 1 : page === totalPages}
            style={{ width: '28px', height: '28px', borderRadius: '8px', border: '1px solid #e5e7eb', backgroundColor: 'white', cursor: (idx === 0 ? page === 1 : page === totalPages) ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: (idx === 0 ? page === 1 : page === totalPages) ? '#d1d5db' : '#6b7280', fontSize: '14px' }}>
            {arrow}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Toggle switch component ──────────────────────────────────────────────────

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button onClick={onChange} style={{ width: '40px', height: '22px', borderRadius: '11px', backgroundColor: checked ? '#2563eb' : '#d1d5db', border: 'none', cursor: 'pointer', position: 'relative', transition: 'background-color 0.2s', flexShrink: 0 }}>
      <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: 'white', position: 'absolute', top: '3px', left: checked ? '21px' : '3px', transition: 'left 0.2s' }} />
    </button>
  )
}

// ─── Credit Wallet Modal ──────────────────────────────────────────────────────

function CreditModal({ orgId, onClose, onSuccess }: { orgId: string; onClose: () => void; onSuccess: () => void }) {
  const [minutes, setMinutes] = useState('')
  const [rate, setRate] = useState('')
  const [desc, setDesc] = useState('Manual top-up by Super Admin')
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!minutes || !rate) { toast.error('Fill in all fields'); return }
    setSaving(true)
    try {
      await adminApi.creditWallet(orgId, { minutes: Number(minutes), rate_per_minute: Number(rate), description: desc })
      toast.success('Wallet credited successfully')
      onSuccess()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Failed to credit wallet')
    } finally { setSaving(false) }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 100, backgroundColor: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
      <div style={{ backgroundColor: 'white', borderRadius: '20px', padding: '28px', width: '100%', maxWidth: '420px', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#111827', margin: 0 }}>Credit Wallet</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', display: 'flex' }}><X size={18} /></button>
        </div>
        {[
          { label: 'Number of minutes', val: minutes, set: setMinutes, type: 'number', placeholder: '100' },
          { label: 'Rate per minute (INR)', val: rate, set: setRate, type: 'number', placeholder: '0.50' },
        ].map(({ label, val, set, type, placeholder }) => (
          <div key={label} style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '13px', fontWeight: '500', color: '#374151', display: 'block', marginBottom: '6px' }}>{label}</label>
            <input type={type} placeholder={placeholder} value={val} onChange={e => set(e.target.value)}
              style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 14px', fontSize: '14px', color: '#111827', backgroundColor: '#f9fafb', outline: 'none', boxSizing: 'border-box' }}
              onFocus={e => (e.currentTarget.style.borderColor = '#93c5fd')}
              onBlur={e => (e.currentTarget.style.borderColor = '#e5e7eb')} />
          </div>
        ))}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ fontSize: '13px', fontWeight: '500', color: '#374151', display: 'block', marginBottom: '6px' }}>Description</label>
          <input value={desc} onChange={e => setDesc(e.target.value)}
            style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 14px', fontSize: '14px', color: '#111827', backgroundColor: '#f9fafb', outline: 'none', boxSizing: 'border-box' }}
            onFocus={e => (e.currentTarget.style.borderColor = '#93c5fd')}
            onBlur={e => (e.currentTarget.style.borderColor = '#e5e7eb')} />
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={onClose} style={{ flex: 1, padding: '11px', border: '1px solid #e5e7eb', borderRadius: '50px', backgroundColor: 'white', fontSize: '13px', fontWeight: '600', color: '#374151', cursor: 'pointer' }}>Cancel</button>
          <button onClick={submit} disabled={saving} style={{ flex: 1, padding: '11px', border: 'none', borderRadius: '50px', backgroundColor: saving ? '#93c5fd' : '#2563eb', fontSize: '13px', fontWeight: '600', color: 'white', cursor: saving ? 'not-allowed' : 'pointer' }}>
            {saving ? 'Processing…' : 'Credit Wallet'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Edit Modal ───────────────────────────────────────────────────────────────

function EditModal({ org, onClose, onSuccess }: { org: OrgDetail; onClose: () => void; onSuccess: (name: string) => void }) {
  const [name, setName] = useState(org.name)
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!name.trim()) { toast.error('Name is required'); return }
    setSaving(true)
    try {
      await adminApi.updateOrg(org.id, { name: name.trim() })
      toast.success('Organization updated')
      onSuccess(name.trim())
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Failed to update')
    } finally { setSaving(false) }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 100, backgroundColor: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
      <div style={{ backgroundColor: 'white', borderRadius: '20px', padding: '28px', width: '100%', maxWidth: '400px', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#111827', margin: 0 }}>Edit Organization</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', display: 'flex' }}><X size={18} /></button>
        </div>
        <div style={{ marginBottom: '20px' }}>
          <label style={{ fontSize: '13px', fontWeight: '500', color: '#374151', display: 'block', marginBottom: '6px' }}>Organization Name</label>
          <input value={name} onChange={e => setName(e.target.value)}
            style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 14px', fontSize: '14px', color: '#111827', backgroundColor: '#f9fafb', outline: 'none', boxSizing: 'border-box' }}
            onFocus={e => (e.currentTarget.style.borderColor = '#93c5fd')}
            onBlur={e => (e.currentTarget.style.borderColor = '#e5e7eb')} />
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={onClose} style={{ flex: 1, padding: '11px', border: '1px solid #e5e7eb', borderRadius: '50px', backgroundColor: 'white', fontSize: '13px', fontWeight: '600', color: '#374151', cursor: 'pointer' }}>Cancel</button>
          <button onClick={submit} disabled={saving} style={{ flex: 1, padding: '11px', border: 'none', borderRadius: '50px', backgroundColor: saving ? '#93c5fd' : '#2563eb', fontSize: '13px', fontWeight: '600', color: 'white', cursor: saving ? 'not-allowed' : 'pointer' }}>
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Tab: Overview ────────────────────────────────────────────────────────────

function OverviewTab({ org }: { org: OrgDetail }) {
  const statCards = [
    { label: 'Total users', value: org.stats.total_users.toLocaleString('en-IN'), icon: <Users size={20} style={{ color: '#2563eb' }} />, bg: '#eff6ff' },
    { label: 'Total campaign', value: org.stats.total_campaigns.toLocaleString('en-IN'), icon: <Rocket size={20} style={{ color: '#7c3aed' }} />, bg: '#f5f3ff' },
    { label: 'Total calls', value: org.stats.total_calls.toLocaleString('en-IN'), icon: <Phone size={20} style={{ color: '#0891b2' }} />, bg: '#ecfeff' },
    { label: 'Total minutes used', value: org.stats.total_minutes.toLocaleString('en-IN'), icon: <Clock size={20} style={{ color: '#0284c7' }} />, bg: '#f0f9ff' },
  ]

  const walletCards = [
    { label: 'Minutes balance', value: org.wallet.minutes_balance.toLocaleString('en-IN') },
    { label: 'Rate per minute', value: `₹${org.wallet.rate_per_minute}` },
    { label: 'Total amount paid', value: `₹${org.wallet.total_amount_paid.toLocaleString('en-IN')}` },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        {statCards.map(({ label, value, icon, bg }) => (
          <div key={label} style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <p style={{ fontSize: '13px', color: '#6b7280', fontWeight: '500', margin: 0 }}>{label}</p>
              <div style={{ width: '36px', height: '36px', borderRadius: '10px', backgroundColor: bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{icon}</div>
            </div>
            <p style={{ fontSize: '28px', fontWeight: '700', color: '#111827', margin: 0 }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Wallet summary */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', padding: '20px' }}>
        <p style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '16px' }}>Wallet summery</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          {walletCards.map(({ label, value }) => (
            <div key={label} style={{ backgroundColor: '#f8fafc', borderRadius: '12px', padding: '18px 20px' }}>
              <p style={{ fontSize: '13px', color: '#9ca3af', fontWeight: '500', marginBottom: '8px' }}>{label}</p>
              <p style={{ fontSize: '22px', fontWeight: '700', color: '#111827', margin: 0 }}>{value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Tab: Users ───────────────────────────────────────────────────────────────

function UsersTab({ users: initial }: { orgId: string; users: UserRow[] }) {
  const [users, setUsers] = useState<UserRow[]>(initial)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const filtered = users.filter(u =>
    `${u.first_name} ${u.last_name} ${u.email}`.toLowerCase().includes(search.toLowerCase())
  )
  const paginated = filtered.slice((page - 1) * perPage, page * perPage)

  const toggle = async (user: UserRow) => {
    try {
      await adminApi.toggleUser(user.id)
      setUsers(prev => prev.map(u => u.id === user.id ? { ...u, is_active: !u.is_active } : u))
      toast.success(`User ${user.is_active ? 'deactivated' : 'activated'}`)
    } catch { toast.error('Failed to update user') }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 14px' }}>
          <Search size={14} style={{ color: '#9ca3af', flexShrink: 0 }} />
          <input type="text" placeholder="Search" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }}
            style={{ flex: 1, border: 'none', outline: 'none', fontSize: '13px', color: '#374151', backgroundColor: 'transparent' }} />
        </div>
        <button style={{ display: 'flex', alignItems: 'center', gap: '6px', backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 14px', fontSize: '13px', fontWeight: '500', color: '#2563eb', cursor: 'pointer' }}>
          <SlidersHorizontal size={14} /> Filter
        </button>
      </div>

      {/* Table */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
              {['Name', 'Email', 'Role', 'Status', 'Last login', 'Action'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '13px', fontWeight: '700', color: '#374151' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr><td colSpan={6} style={{ padding: '40px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>No users found</td></tr>
            ) : paginated.map((u, i) => (
              <tr key={u.id} style={{ borderBottom: i < paginated.length - 1 ? '1px solid #f3f4f6' : 'none' }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}>
                <td style={{ padding: '14px 20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: '600', color: '#6b7280', flexShrink: 0 }}>
                      {u.first_name?.[0]?.toUpperCase()}
                    </div>
                    <div>
                      <p style={{ fontSize: '13px', fontWeight: '600', color: '#111827', margin: 0, lineHeight: '1.3' }}>{u.first_name} {u.last_name}</p>
                      <p style={{ fontSize: '11px', color: '#9ca3af', margin: 0, lineHeight: '1.3' }}>{u.email}</p>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>{u.email}</td>
                <td style={{ padding: '14px 20px', fontSize: '13px', fontWeight: '600', color: '#374151', textTransform: 'capitalize' }}>{u.role}</td>
                <td style={{ padding: '14px 20px' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '12px', fontWeight: '600', color: u.is_active ? '#16a34a' : '#6b7280', backgroundColor: u.is_active ? '#f0fdf4' : '#f3f4f6', padding: '3px 10px', borderRadius: '20px' }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor', display: 'inline-block' }} />
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td style={{ padding: '14px 20px', fontSize: '13px', color: '#6b7280', whiteSpace: 'nowrap' }}>{fmtDateTime(u.last_login_at)}</td>
                <td style={{ padding: '14px 20px' }}>
                  <Toggle checked={u.is_active} onChange={() => toggle(u)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={page} perPage={perPage} total={filtered.length} onPage={setPage} onPerPage={setPerPage} />
      </div>
    </div>
  )
}

// ─── Tab: Campaigns ───────────────────────────────────────────────────────────

const statusStyle: Record<string, { color: string; bg: string }> = {
  active:    { color: '#16a34a', bg: '#f0fdf4' },
  inactive:  { color: '#6b7280', bg: '#f3f4f6' },
  completed: { color: '#6b7280', bg: '#f3f4f6' },
  paused:    { color: '#d97706', bg: '#fffbeb' },
  draft:     { color: '#6b7280', bg: '#f3f4f6' },
}

function CampaignsTab({ campaigns: initial }: { campaigns: CampaignRow[] }) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const filtered = initial.filter(c => c.name.toLowerCase().includes(search.toLowerCase()))
  const paginated = filtered.slice((page - 1) * perPage, page * perPage)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 14px' }}>
          <Search size={14} style={{ color: '#9ca3af', flexShrink: 0 }} />
          <input type="text" placeholder="Search" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }}
            style={{ flex: 1, border: 'none', outline: 'none', fontSize: '13px', color: '#374151', backgroundColor: 'transparent' }} />
        </div>
        <button style={{ display: 'flex', alignItems: 'center', gap: '6px', backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 14px', fontSize: '13px', fontWeight: '500', color: '#2563eb', cursor: 'pointer' }}>
          <SlidersHorizontal size={14} /> Filter
        </button>
      </div>

      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
              {['Campaign name', 'Status', 'Leads', 'Calls', 'Minutes used'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '13px', fontWeight: '700', color: '#374151' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr><td colSpan={5} style={{ padding: '40px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>No campaigns found</td></tr>
            ) : paginated.map((c, i) => {
              const st = statusStyle[c.status?.toLowerCase()] ?? statusStyle.inactive
              return (
                <tr key={c.id} style={{ borderBottom: i < paginated.length - 1 ? '1px solid #f3f4f6' : 'none' }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}>
                  <td style={{ padding: '14px 20px', fontSize: '13px', fontWeight: '500', color: '#111827' }}>{c.name}</td>
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '12px', fontWeight: '600', color: st.color, backgroundColor: st.bg, padding: '3px 10px', borderRadius: '20px', textTransform: 'capitalize' }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor', display: 'inline-block' }} />
                      {c.status}
                    </span>
                  </td>
                  <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>{(c.stats?.total_leads ?? 0).toLocaleString('en-IN')}</td>
                  <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>{(c.stats?.total_calls ?? 0).toLocaleString('en-IN')}</td>
                  <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>{(c.stats?.total_minutes ?? 0).toLocaleString('en-IN')}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <Pagination page={page} perPage={perPage} total={filtered.length} onPage={setPage} onPerPage={setPerPage} />
      </div>
    </div>
  )
}

// ─── Tab: Wallet ──────────────────────────────────────────────────────────────

function WalletTab({ orgId, onCreditClick }: { orgId: string; onCreditClick: () => void }) {
  const [data, setData] = useState<WalletData | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const load = () => {
    setLoading(true)
    adminApi.orgWallet(orgId)
      .then(res => setData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [orgId])

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>Loading wallet…</div>
  if (!data) return null

  const txns = data.transactions ?? []
  const paginated = txns.slice((page - 1) * perPage, page * perPage)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Wallet balance section */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <p style={{ fontSize: '15px', fontWeight: '700', color: '#111827', margin: 0 }}>Wallet balance</p>
          <button
            onClick={onCreditClick}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '10px', padding: '10px 18px', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}
          >
            <CreditCard size={15} /> Credit wallet
          </button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          {[
            { label: 'Minutes balance', value: (data.wallet?.minutes_balance ?? 0).toLocaleString('en-IN') },
            { label: 'Rate per minute', value: `₹${data.wallet?.rate_per_minute ?? 0}` },
            { label: 'Total amount paid', value: `₹${(data.wallet?.total_amount_paid ?? 0).toLocaleString('en-IN')}` },
          ].map(({ label, value }) => (
            <div key={label} style={{ backgroundColor: '#f8fafc', borderRadius: '12px', padding: '18px 20px' }}>
              <p style={{ fontSize: '13px', color: '#9ca3af', fontWeight: '500', marginBottom: '8px' }}>{label}</p>
              <p style={{ fontSize: '22px', fontWeight: '700', color: '#111827', margin: 0 }}>{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Transactions table */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
              {['Date', 'Transaction type', 'Minutes added/used', 'Amount', 'Balance after transaction'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '13px', fontWeight: '700', color: '#374151', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr><td colSpan={5} style={{ padding: '40px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>No transactions yet</td></tr>
            ) : paginated.map((tx, i) => {
              const isCredit = tx.type === 'credit'
              return (
                <tr key={tx.id} style={{ borderBottom: i < paginated.length - 1 ? '1px solid #f3f4f6' : 'none' }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}>
                  <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151', whiteSpace: 'nowrap' }}>{fmt(tx.created_at)}</td>
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{ fontSize: '13px', fontWeight: '600', color: isCredit ? '#16a34a' : '#dc2626', textTransform: 'capitalize' }}>{tx.type}</span>
                  </td>
                  <td style={{ padding: '14px 20px', fontSize: '13px', fontWeight: '600', color: isCredit ? '#16a34a' : '#dc2626' }}>
                    {isCredit ? '+' : '-'}{Math.abs(tx.minutes).toLocaleString('en-IN')}
                  </td>
                  <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>₹{tx.amount_inr.toLocaleString('en-IN')}</td>
                  <td style={{ padding: '14px 20px', fontSize: '13px', color: '#374151' }}>{tx.balance_after.toLocaleString('en-IN')}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <Pagination page={page} perPage={perPage} total={txns.length} onPage={setPage} onPerPage={setPerPage} />
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type Tab = 'overview' | 'users' | 'campaigns' | 'wallet'

export default function OrgDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [org, setOrg] = useState<OrgDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('overview')
  const [showCredit, setShowCredit] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  useEffect(() => {
    if (!id) return
    adminApi.org(id)
      .then(res => setOrg(res.data))
      .catch(() => toast.error('Failed to load organization'))
      .finally(() => setLoading(false))
  }, [id])

  const toggleStatus = async () => {
    if (!org) return
    setToggling(true)
    try {
      await adminApi.updateOrg(org.id, { is_active: !org.is_active })
      setOrg(prev => prev ? { ...prev, is_active: !prev.is_active } : prev)
      toast.success(`Organization ${org.is_active ? 'suspended' : 'activated'}`)
    } catch { toast.error('Failed to update status') }
    finally { setToggling(false) }
  }

  const handleDelete = async () => {
    if (!org) return
    setDeleting(true)
    try {
      await adminApi.deleteOrg(org.id)
      toast.success('Organization deleted')
      router.push('/superadmin/organizations')
    } catch { toast.error('Failed to delete organization'); setDeleting(false) }
  }

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {[...Array(3)].map((_, i) => <div key={i} style={{ height: '80px', backgroundColor: '#e5e7eb', borderRadius: '12px' }} />)}
    </div>
  )

  if (!org) return (
    <div style={{ textAlign: 'center', padding: '60px', fontSize: '14px', color: '#9ca3af' }}>Organization not found.</div>
  )

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'users', label: 'Users' },
    { key: 'campaigns', label: 'Campaigns' },
    { key: 'wallet', label: 'Wallet' },
  ]

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

        {/* Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#9ca3af' }}>
          <button onClick={() => router.push('/superadmin/organizations')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', fontSize: '13px', padding: 0 }}>
            Organizations
          </button>
          <span>{'<'}</span>
          <span style={{ color: '#6b7280' }}>{org.name}</span>
        </div>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h1 style={{ fontSize: '26px', fontWeight: '800', color: '#111827', margin: '0 0 4px 0' }}>{org.name}</h1>
            <p style={{ fontSize: '14px', color: '#9ca3af', margin: 0 }}>{org.slug}</p>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            {/* Active/Suspended toggle */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '8px 14px', backgroundColor: 'white' }}>
              <span style={{ fontSize: '13px', color: org.is_active ? '#9ca3af' : '#374151', fontWeight: org.is_active ? '400' : '600' }}>Suspended</span>
              <Toggle checked={org.is_active} onChange={toggling ? () => {} : toggleStatus} />
              <span style={{ fontSize: '13px', color: org.is_active ? '#16a34a' : '#9ca3af', fontWeight: org.is_active ? '600' : '400' }}>Active</span>
            </div>

            {/* Edit */}
            <button onClick={() => setShowEdit(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '9px 16px', fontSize: '13px', fontWeight: '600', color: '#374151', cursor: 'pointer' }}>
              <Pencil size={14} style={{ color: '#2563eb' }} /> Edit
            </button>

            {/* Delete */}
            <button onClick={() => setConfirmDelete(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '9px 16px', fontSize: '13px', fontWeight: '600', color: '#374151', cursor: 'pointer' }}>
              <Trash2 size={14} style={{ color: '#374151' }} /> Delete
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '0', borderBottom: '1px solid #e5e7eb' }}>
          {tabs.map(({ key, label }) => (
            <button key={key} onClick={() => setTab(key)}
              style={{
                padding: '10px 20px', fontSize: '14px', fontWeight: tab === key ? '600' : '400',
                color: tab === key ? '#2563eb' : '#6b7280', background: 'none', border: 'none',
                borderBottom: tab === key ? '2px solid #2563eb' : '2px solid transparent',
                cursor: 'pointer', marginBottom: '-1px', transition: 'all 0.15s',
              }}>
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === 'overview'   && <OverviewTab org={org} />}
        {tab === 'users'      && <UsersTab orgId={org.id} users={org.users} />}
        {tab === 'campaigns'  && <CampaignsTab campaigns={org.campaigns} />}
        {tab === 'wallet'     && <WalletTab orgId={org.id} onCreditClick={() => setShowCredit(true)} />}
      </div>

      {/* Credit Wallet Modal */}
      {showCredit && (
        <CreditModal
          orgId={org.id}
          onClose={() => setShowCredit(false)}
          onSuccess={() => { setShowCredit(false); setTab('wallet') }}
        />
      )}

      {/* Edit Modal */}
      {showEdit && (
        <EditModal
          org={org}
          onClose={() => setShowEdit(false)}
          onSuccess={(name) => { setOrg(prev => prev ? { ...prev, name } : prev); setShowEdit(false) }}
        />
      )}

      {/* Delete Confirm Modal */}
      {confirmDelete && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 100, backgroundColor: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
          <div style={{ backgroundColor: 'white', borderRadius: '20px', padding: '28px', width: '100%', maxWidth: '380px', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '50%', backgroundColor: '#fef2f2', border: '4px solid #fecaca', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <Trash2 size={20} style={{ color: '#dc2626' }} />
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#111827', textAlign: 'center', marginBottom: '8px' }}>Delete Organization</h3>
            <p style={{ fontSize: '13px', color: '#6b7280', textAlign: 'center', marginBottom: '24px' }}>
              Are you sure you want to delete <strong>{org.name}</strong>? This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={() => setConfirmDelete(false)} style={{ flex: 1, padding: '11px', border: '1px solid #e5e7eb', borderRadius: '50px', backgroundColor: 'white', fontSize: '13px', fontWeight: '600', color: '#374151', cursor: 'pointer' }}>Cancel</button>
              <button onClick={handleDelete} disabled={deleting} style={{ flex: 1, padding: '11px', border: 'none', borderRadius: '50px', backgroundColor: deleting ? '#fca5a5' : '#dc2626', fontSize: '13px', fontWeight: '600', color: 'white', cursor: deleting ? 'not-allowed' : 'pointer' }}>
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
