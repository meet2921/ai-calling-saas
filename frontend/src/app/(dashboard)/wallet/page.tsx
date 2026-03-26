'use client'

import { useEffect, useState } from 'react'
import { walletApi } from '@/lib/api/wallet'

interface WalletSummary {
  minutes_balance: number
  rate_per_minute: number
  total_minutes_purchased: number
  total_minutes_used: number
  total_amount_paid: number
  estimated_cost_remaining: number
}

interface Transaction {
  id: string
  type: string
  minutes: number
  amount_inr: number
  rate_per_minute: number
  balance_after: number
  description: string | null
  created_at: string
}

const fmt = (n: number) => n?.toLocaleString('en-IN') ?? '0'
const fmtCurrency = (n: number) => `₹${fmt(n)}`
const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Calcutta' })

export default function WalletPage() {
  const [summary, setSummary] = useState<WalletSummary | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  useEffect(() => {
    Promise.all([walletApi.summary(), walletApi.transactions()])
      .then(([sumRes, txRes]) => {
        setSummary(sumRes.data)
        const data = txRes.data
        const txList = Array.isArray(data) ? data : data?.transactions ?? []
        setTransactions(txList)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>Loading wallet...</div>
  }

  const balance = summary?.minutes_balance ?? 0
  const isLow = balance === 0
  const estimatedValue = summary?.estimated_cost_remaining ?? 0

  const totalPages = Math.max(1, Math.ceil(transactions.length / pageSize))
  const paginated = transactions.slice((page - 1) * pageSize, page * pageSize)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Wallet balance card */}
      <div style={{
        backgroundColor: 'white', border: '1px solid #e5e7eb',
        borderRadius: '16px', padding: '24px 28px',
      }}>
        {/* Header row */}
        <div style={{ marginBottom: '20px' }}>
          <p style={{ fontSize: '16px', fontWeight: '700', color: '#111827', margin: 0 }}>Wallet balance</p>
        </div>

        {/* Balance cards row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '16px' }}>

          {/* Minutes balance */}
          <div style={{
            backgroundColor: isLow ? '#fff1f2' : '#f8faff',
            border: `1px solid ${isLow ? '#fecdd3' : '#e5e7eb'}`,
            borderRadius: '12px', padding: '20px 22px',
          }}>
            <p style={{ fontSize: '13px', color: isLow ? '#ef4444' : '#6b7280', margin: '0 0 10px' }}>
              Minutes balance
            </p>
            <p style={{
              fontSize: '32px', fontWeight: '700',
              color: isLow ? '#ef4444' : '#111827', margin: 0,
            }}>
              {fmt(balance)}
            </p>
          </div>

          {/* Rate per minute */}
          <div style={{
            backgroundColor: '#f8faff', border: '1px solid #e5e7eb',
            borderRadius: '12px', padding: '20px 22px',
          }}>
            <p style={{ fontSize: '13px', color: '#6b7280', margin: '0 0 10px' }}>Rate per minute</p>
            <p style={{ fontSize: '32px', fontWeight: '700', color: '#111827', margin: 0 }}>
              {fmtCurrency(summary?.rate_per_minute ?? 0)}
            </p>
          </div>

          {/* Estimated remaining value */}
          <div style={{
            backgroundColor: '#f8faff', border: '1px solid #e5e7eb',
            borderRadius: '12px', padding: '20px 22px',
          }}>
            <p style={{ fontSize: '13px', color: '#6b7280', margin: '0 0 10px' }}>Estimated remaining value</p>
            <p style={{ fontSize: '32px', fontWeight: '700', color: '#111827', margin: 0 }}>
              {estimatedValue > 0 ? fmtCurrency(estimatedValue) : '0'}
            </p>
          </div>
        </div>

        {/* Contact note */}
        <p style={{ fontSize: '13px', color: isLow ? '#ef4444' : '#9ca3af', margin: 0 }}>
          Contact your super admin to add more wallet credits.
        </p>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        {[
          { label: 'Total Minutes Purchased', value: `${fmt(summary?.total_minutes_purchased ?? 0)} min` },
          { label: 'Total Minutes Used', value: `${fmt(summary?.total_minutes_used ?? 0)} min` },
          { label: 'Total Amount Paid (INR)', value: fmtCurrency(summary?.total_amount_paid ?? 0) },
          { label: 'Estimated Cost Remaining (INR)', value: fmtCurrency(summary?.estimated_cost_remaining ?? 0) },
        ].map(card => (
          <div key={card.label} style={{
            backgroundColor: 'white', border: '1px solid #e5e7eb',
            borderRadius: '14px', padding: '20px 22px',
          }}>
            <p style={{ fontSize: '13px', color: '#6b7280', margin: '0 0 10px', lineHeight: '1.4' }}>{card.label}</p>
            <p style={{ fontSize: '26px', fontWeight: '700', color: '#111827', margin: 0 }}>{card.value}</p>
          </div>
        ))}
      </div>

      {/* Transactions table */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '14px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
              {['Date', 'Transaction type', 'Minutes', 'Amount', 'Balance after', 'Description'].map(h => (
                <th key={h} style={{
                  textAlign: 'left', padding: '14px 20px',
                  fontSize: '14px', fontWeight: '700', color: '#111827',
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '60px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>
                  No transactions yet
                </td>
              </tr>
            ) : (
              paginated.map((tx, i) => {
                const isCredit = tx.type?.toLowerCase() === 'credit'
                return (
                  <tr
                    key={tx.id}
                    style={{ borderBottom: i < paginated.length - 1 ? '1px solid #f3f4f6' : 'none' }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = '#f9fafb'}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                  >
                    <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>
                      {fmtDate(tx.created_at)}
                    </td>
                    <td style={{ padding: '13px 20px', fontSize: '13px', fontWeight: '600', color: isCredit ? '#16a34a' : '#ef4444' }}>
                      {isCredit ? 'Credit' : 'Debit'}
                    </td>
                    <td style={{ padding: '13px 20px', fontSize: '13px', fontWeight: '600', color: isCredit ? '#16a34a' : '#ef4444' }}>
                      {isCredit ? '+' : '-'}{fmt(Math.abs(tx.minutes))}
                    </td>
                    <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151' }}>
                      {fmtCurrency(tx.amount_inr)}
                    </td>
                    <td style={{ padding: '13px 20px', fontSize: '13px', color: '#374151', fontWeight: '500' }}>
                      {fmt(tx.balance_after)}
                    </td>
                    <td style={{ padding: '13px 20px', fontSize: '13px', color: '#6b7280' }}>
                      {tx.description ?? '—'}
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
              style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}
            >
              {[10, 25, 50].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
            <span>Items per page</span>
            <span style={{ marginLeft: '8px', color: '#374151' }}>
              {transactions.length === 0 ? '0' : `${(page - 1) * pageSize + 1}-${Math.min(page * pageSize, transactions.length)}`} of {transactions.length} items
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <select
              value={page}
              onChange={e => setPage(Number(e.target.value))}
              style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '6px', fontSize: '13px', color: '#374151', backgroundColor: 'white', cursor: 'pointer' }}
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
      </div>

    </div>
  )
}
