'use client'

import { useEffect, useState } from 'react'
import { adminApi } from '@/lib/api/admin'
import { Search, SlidersHorizontal, X } from 'lucide-react'
import { toast } from 'sonner'

interface User {
  id: string
  first_name: string
  last_name: string
  email: string
  role: string
  organization_name: string
  organization_slug: string
  is_active: boolean
  last_login_at?: string
}

function SkeletonRow() {
  return (
    <tr style={{ borderBottom: '1px solid #f3f4f6' }}>
      {[40, 60, 40, 40, 50, 60, 30].map((w, i) => (
        <td key={i} style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {i === 0 && <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#e5e7eb', flexShrink: 0 }} />}
            <div style={{ height: '12px', width: `${w}%`, backgroundColor: '#e5e7eb', borderRadius: '6px' }} />
          </div>
        </td>
      ))}
    </tr>
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      style={{
        width: '40px', height: '22px', borderRadius: '11px',
        backgroundColor: checked ? '#2563eb' : '#d1d5db',
        border: 'none', cursor: 'pointer', position: 'relative',
        transition: 'background-color 0.2s', flexShrink: 0,
      }}
    >
      <div style={{
        width: '16px', height: '16px', borderRadius: '50%',
        backgroundColor: 'white', position: 'absolute',
        top: '3px', left: checked ? '21px' : '3px',
        transition: 'left 0.2s',
      }} />
    </button>
  )
}

function fmtDate(iso?: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Calcutta',
  })
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterOpen, setFilterOpen] = useState(false)
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'manager'>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  useEffect(() => {
    adminApi.users()
      .then(res => {
        const list = Array.isArray(res.data) ? res.data : res.data?.users ?? []
        setUsers(list)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = users.filter(u => {
    const matchSearch =
      `${u.first_name} ${u.last_name} ${u.email} ${u.organization_name}`
        .toLowerCase().includes(search.toLowerCase())
    const matchRole = roleFilter === 'all' || u.role === roleFilter
    const matchStatus =
      statusFilter === 'all' ||
      (statusFilter === 'active' && u.is_active) ||
      (statusFilter === 'inactive' && !u.is_active)
    return matchSearch && matchRole && matchStatus
  })

  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage))
  const paginated = filtered.slice((page - 1) * perPage, page * perPage)
  const hasFilters = search !== '' || roleFilter !== 'all' || statusFilter !== 'all'

  const clearFilters = () => {
    setSearch('')
    setRoleFilter('all')
    setStatusFilter('all')
    setPage(1)
  }

  const toggleUser = async (user: User) => {
    try {
      await adminApi.toggleUser(user.id)
      setUsers(prev =>
        prev.map(u => u.id === user.id ? { ...u, is_active: !u.is_active } : u)
      )
      toast.success(`User ${user.is_active ? 'deactivated' : 'activated'}`)
    } catch {
      toast.error('Failed to update user status')
    }
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
            placeholder="Search by name, email or organization..."
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
            {(roleFilter !== 'all' || statusFilter !== 'all') && (
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#2563eb', display: 'inline-block', marginLeft: '2px' }} />
            )}
          </button>

          {filterOpen && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 8px)', left: 0, zIndex: 50,
              backgroundColor: 'white', border: '1px solid #e5e7eb',
              borderRadius: '12px', padding: '14px', minWidth: '180px',
              boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
            }}>
              {/* Role filter */}
              <p style={{ fontSize: '11px', fontWeight: '600', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>Role</p>
              {(['all', 'admin', 'manager'] as const).map(r => (
                <button key={r} onClick={() => { setRoleFilter(r); setPage(1) }}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '7px 10px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                    fontSize: '13px', fontWeight: roleFilter === r ? '600' : '400',
                    backgroundColor: roleFilter === r ? '#eff6ff' : 'transparent',
                    color: roleFilter === r ? '#2563eb' : '#374151',
                  }}>
                  {r === 'all' ? 'All roles' : r.charAt(0).toUpperCase() + r.slice(1)}
                </button>
              ))}

              <div style={{ height: '1px', backgroundColor: '#f3f4f6', margin: '10px 0' }} />

              {/* Status filter */}
              <p style={{ fontSize: '11px', fontWeight: '600', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>Status</p>
              {(['all', 'active', 'inactive'] as const).map(s => (
                <button key={s} onClick={() => { setStatusFilter(s); setPage(1) }}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '7px 10px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                    fontSize: '13px', fontWeight: statusFilter === s ? '600' : '400',
                    backgroundColor: statusFilter === s ? '#eff6ff' : 'transparent',
                    color: statusFilter === s ? '#2563eb' : '#374151',
                  }}>
                  {s === 'all' ? 'All statuses' : s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}

              {(roleFilter !== 'all' || statusFilter !== 'all') && (
                <button onClick={() => { setRoleFilter('all'); setStatusFilter('all'); setPage(1); setFilterOpen(false) }}
                  style={{ display: 'block', width: '100%', textAlign: 'center', marginTop: '10px', padding: '7px', borderRadius: '8px', border: '1px solid #e5e7eb', backgroundColor: 'white', fontSize: '12px', fontWeight: '600', color: '#6b7280', cursor: 'pointer' }}>
                  Clear filters
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                {['User', 'Organization', 'Role', 'Status', 'Last Login', 'Active'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '13px', fontWeight: '700', color: '#374151' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>{[...Array(5)].map((_, i) => <SkeletonRow key={i} />)}</tbody>
          </table>
        </div>

      ) : users.length === 0 ? (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '16px', padding: '80px 24px',
        }}>
          <div style={{ fontSize: '72px', marginBottom: '16px', lineHeight: 1 }}>👥</div>
          <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>No users yet</p>
          <p style={{ fontSize: '14px', color: '#6b7280', textAlign: 'center', maxWidth: '320px' }}>
            Users will appear here once organizations are created with admin accounts.
          </p>
        </div>

      ) : paginated.length === 0 && hasFilters ? (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '16px', padding: '80px 24px',
        }}>
          <div style={{ fontSize: '72px', marginBottom: '16px', lineHeight: 1 }}>🔍</div>
          <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>No users found</p>
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
                {['User', 'Organization', 'Role', 'Status', 'Last Login', 'Active'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '14px 20px', fontSize: '13px', fontWeight: '700', color: '#374151', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginated.map((user, i) => (
                <tr key={user.id}
                  style={{ borderBottom: i < paginated.length - 1 ? '1px solid #f3f4f6' : 'none' }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                >
                  {/* User */}
                  <td style={{ padding: '14px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{
                        width: '34px', height: '34px', borderRadius: '50%',
                        backgroundColor: '#e5e7eb', display: 'flex', alignItems: 'center',
                        justifyContent: 'center', fontSize: '13px', fontWeight: '600',
                        color: '#6b7280', flexShrink: 0,
                      }}>
                        {user.first_name?.[0]?.toUpperCase()}
                      </div>
                      <div>
                        <p style={{ fontSize: '13px', fontWeight: '600', color: '#111827', margin: 0, lineHeight: '1.3' }}>
                          {user.first_name} {user.last_name}
                        </p>
                        <p style={{ fontSize: '11px', color: '#9ca3af', margin: 0, lineHeight: '1.3' }}>{user.email}</p>
                      </div>
                    </div>
                  </td>

                  {/* Organization */}
                  <td style={{ padding: '14px 20px' }}>
                    <p style={{ fontSize: '13px', fontWeight: '500', color: '#111827', margin: 0, lineHeight: '1.3' }}>{user.organization_name}</p>
                    <p style={{ fontSize: '11px', color: '#9ca3af', margin: 0, lineHeight: '1.3' }}>{user.organization_slug}</p>
                  </td>

                  {/* Role */}
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{
                      fontSize: '12px', fontWeight: '600', textTransform: 'capitalize',
                      color: user.role === 'admin' ? '#7c3aed' : '#0891b2',
                      backgroundColor: user.role === 'admin' ? '#f5f3ff' : '#ecfeff',
                      padding: '3px 10px', borderRadius: '20px',
                    }}>
                      {user.role}
                    </span>
                  </td>

                  {/* Status */}
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: '5px',
                      fontSize: '12px', fontWeight: '600',
                      color: user.is_active ? '#16a34a' : '#6b7280',
                      backgroundColor: user.is_active ? '#f0fdf4' : '#f3f4f6',
                      padding: '3px 10px', borderRadius: '20px',
                    }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor', display: 'inline-block' }} />
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>

                  {/* Last Login */}
                  <td style={{ padding: '14px 20px', fontSize: '13px', color: '#6b7280', whiteSpace: 'nowrap' }}>
                    {fmtDate(user.last_login_at)}
                  </td>

                  {/* Toggle */}
                  <td style={{ padding: '14px 20px' }}>
                    <Toggle checked={user.is_active} onChange={() => toggleUser(user)} />
                  </td>
                </tr>
              ))}
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
